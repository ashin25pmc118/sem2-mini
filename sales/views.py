import json
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import Sale, SaleItem, Purchase, Supplier, Customer, Expense
from .forms import SaleForm, SaleItemForm, PurchaseForm, SupplierForm, CustomerForm, ExpenseForm
from store.models import Product, ProductCategory
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import csv
from decimal import Decimal

# ===================== POS =====================

@login_required
def pos_billing_view(request):
    bakery = request.user.bakery

    if request.method == 'POST':
        is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json'
        if is_ajax:
            try:
                data = json.loads(request.body)
                cart_data = data.get('cart', [])
                payment_method = data.get('payment_method', 'Cash')
                customer_id = data.get('customer_id') or None
                discount_type = data.get('discount_type', 'Flat')
                discount_value = float(data.get('discount_value', 0.0))
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        else:
            cart_data = json.loads(request.POST.get('cart_json', '[]'))
            payment_method = request.POST.get('payment_method', 'Cash')
            customer_id = request.POST.get('customer_id') or None
            discount_type = request.POST.get('discount_type', 'Flat')
            discount_value = float(request.POST.get('discount_value', 0.0) or 0)

        if not cart_data:
            if is_ajax: return JsonResponse({'success': False, 'error': 'Cart is empty'}, status=400)
            return redirect('pos_billing')

        with transaction.atomic():
            customer = None
            if customer_id:
                try:
                    customer = Customer.objects.get(pk=customer_id, bakery=bakery)
                except Customer.DoesNotExist:
                    pass

            sale = Sale.objects.create(
                bakery=bakery,
                cashier=request.user,
                customer=customer,
                payment_method=payment_method,
                discount_type=discount_type,
                discount_value=discount_value,
                subtotal=Decimal('0.00'),
                tax_amount=Decimal('0.00'),
                total_amount=Decimal('0.00')
            )
            
            subtotal = Decimal('0.00')
            tax_total = Decimal('0.00')
            
            for ci in cart_data:
                try:
                    # Concurrency control: select_for_update locks the row
                    product = Product.objects.select_for_update().get(pk=ci['id'], bakery=bakery)
                    qty = Decimal(str(ci['qty']))
                    sell_unit = ci.get('sell_unit', 'nos')
                    price = product.packet_selling_price if sell_unit == 'pkt' and product.enable_packet_selling else product.selling_price
                    # Stock check: packets consume packet_size nos each
                    stock_needed = qty * product.packet_size if sell_unit == 'pkt' and product.enable_packet_selling else qty
                    if product.stock_quantity < stock_needed:
                        raise ValueError(f"Not enough stock for {product.name}. Available: {product.stock_quantity}")
                    SaleItem.objects.create(
                        sale=sale, product=product,
                        quantity=qty, price_at_sale=price, sell_unit=sell_unit
                    )
                    item_sub = qty * Decimal(str(price))
                    item_tax = item_sub * (Decimal(str(product.tax_percentage)) / Decimal('100'))
                    subtotal += item_sub
                    tax_total += item_tax
                except Product.DoesNotExist:
                    pass
                except ValueError as e:
                    if is_ajax: return JsonResponse({'success': False, 'error': str(e)}, status=400)
                    return redirect('pos_billing')
            
            # Subtotal, Tax, Discounts
            sale.subtotal = subtotal
            sale.tax_amount = tax_total
            grand_total = Decimal(str(subtotal)) + Decimal(str(tax_total))
            if discount_type == 'Percentage':
                discount_amt = grand_total * (Decimal(str(discount_value)) / Decimal(100))
            else:
                discount_amt = Decimal(str(discount_value))
            
            sale.total_amount = max(Decimal('0.00'), grand_total - discount_amt)
            sale.save()
            
        if is_ajax:
            return JsonResponse({'success': True, 'sale_id': sale.id})
        return redirect('sales_list')

    categories = ProductCategory.objects.filter(bakery=bakery)
    products = Product.objects.filter(bakery=bakery, is_active=True).select_related('category')
    customers = Customer.objects.filter(bakery=bakery)

    products_data = []
    for p in products:
        products_data.append({
            'id': p.id,
            'name': p.name,
            'category_id': p.category_id,
            'category_name': p.category.name if p.category else 'All',
            'selling_price': float(p.selling_price),
            'tax_percentage': float(p.tax_percentage),
            'unit': p.get_unit_display(),
            'image': p.image.url if p.image else '',
            'stock': float(p.stock_quantity),
            'enable_packet_selling': p.enable_packet_selling,
            'packet_size': p.packet_size,
            'packet_label': p.packet_label,
            'packet_selling_price': float(p.packet_selling_price),
        })

    from django.db.models import Max
    last_sale = Sale.objects.aggregate(max_id=Max('id'))
    next_invoice_id = (last_sale['max_id'] or 0) + 1

    return render(request, 'sales/pos_billing.html', {
        'categories': categories,
        'products_json': json.dumps(products_data),
        'customers': customers,
        'next_invoice_id': next_invoice_id,
    })


# ===================== SALES =====================

@login_required
def sales_list_view(request):
    query = request.GET.get('q', '')
    sales = Sale.objects.filter(bakery=request.user.bakery).order_by('-date').select_related('customer', 'cashier')
    
    if query:
        if query.isdigit():
            sales = sales.filter(id=int(query))
        else:
            sales = sales.filter(customer__name__icontains=query)
            
    return render(request, 'sales/sales_list.html', {'sales': sales, 'search_query': query})

@login_required
def generate_invoice_pdf(request, sale_id):
    sale = get_object_or_404(Sale, pk=sale_id, bakery=request.user.bakery)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{sale.id}.pdf"'
    
    p = canvas.Canvas(response, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, f"Bakery Mate - Invoice #{sale.id}")
    p.setFont("Helvetica", 12)
    p.drawString(50, 730, f"Bakery: {sale.bakery.name}")
    p.drawString(50, 710, f"Date: {sale.date.strftime('%Y-%m-%d %H:%M')}")
    if sale.customer:
        p.drawString(50, 690, f"Customer: {sale.customer.name}")
        
    p.drawString(50, 660, "----------------------------------------------------------------------")
    p.drawString(50, 640, "Qty")
    p.drawString(100, 640, "Item")
    p.drawString(350, 640, "Price")
    p.drawString(450, 640, "Total")
    p.drawString(50, 630, "----------------------------------------------------------------------")
    
    y = 610
    items = sale.items.all().select_related('product')
    for item in items:
        p.drawString(50, y, str(item.quantity))
        p.drawString(100, y, item.product.name[:35])
        p.drawString(350, y, f"Rs {item.price_at_sale:.2f}")
        total = float(item.quantity * item.price_at_sale)
        p.drawString(450, y, f"Rs {total:.2f}")
        y -= 20
        if y < 100:
            p.showPage()
            y = 750
            
    p.drawString(50, y, "----------------------------------------------------------------------")
    y -= 25
    
    p.drawString(350, y, "Subtotal:")
    p.drawString(450, y, f"Rs {sale.subtotal}")
    y -= 15
    p.drawString(350, y, "Tax:")
    p.drawString(450, y, f"Rs {sale.tax_amount}")
    y -= 15
    
    if sale.discount_value and float(sale.discount_value) > 0:
        p.drawString(350, y, f"Discount ({sale.discount_type}):")
        p.drawString(450, y, f"- Rs {sale.discount_value}")
        y -= 15
        
    p.setFont("Helvetica-Bold", 14)
    p.drawString(350, y-10, "Total Amount:")
    p.drawString(450, y-10, f"Rs {sale.total_amount}")
    
    p.showPage()
    p.save()
    
    return response

@login_required
def generate_invoice_pdf(request, sale_id):
    sale = get_object_or_404(Sale, pk=sale_id, bakery=request.user.bakery)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{sale.id}.pdf"'
    
    p = canvas.Canvas(response, pagesize=letter)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, 750, f"Bakery Mate - Invoice #{sale.id}")
    p.setFont("Helvetica", 12)
    p.drawString(50, 730, f"Bakery: {sale.bakery.name}")
    p.drawString(50, 710, f"Date: {sale.date.strftime('%Y-%m-%d %H:%M')}")
    if sale.customer:
        p.drawString(50, 690, f"Customer: {sale.customer.name}")
        
    p.drawString(50, 660, "----------------------------------------------------------------------")
    p.drawString(50, 640, "Qty")
    p.drawString(100, 640, "Item")
    p.drawString(350, 640, "Price")
    p.drawString(450, 640, "Total")
    p.drawString(50, 630, "----------------------------------------------------------------------")
    
    y = 610
    items = sale.items.all().select_related('product')
    for item in items:
        p.drawString(50, y, str(item.quantity))
        p.drawString(100, y, item.product.name[:35])
        p.drawString(350, y, f"Rs {item.price_at_sale:.2f}")
        total = float(item.quantity * item.price_at_sale)
        p.drawString(450, y, f"Rs {total:.2f}")
        y -= 20
        if y < 100:
            p.showPage()
            y = 750
            
    p.drawString(50, y, "----------------------------------------------------------------------")
    y -= 25
    
    p.drawString(350, y, "Subtotal:")
    p.drawString(450, y, f"Rs {sale.subtotal}")
    y -= 15
    p.drawString(350, y, "Tax:")
    p.drawString(450, y, f"Rs {sale.tax_amount}")
    y -= 15
    
    if sale.discount_value and float(sale.discount_value) > 0:
        p.drawString(350, y, f"Discount ({sale.discount_type}):")
        p.drawString(450, y, f"- Rs {sale.discount_value}")
        y -= 15
        
    p.setFont("Helvetica-Bold", 14)
    p.drawString(350, y-10, "Total Amount:")
    p.drawString(450, y-10, f"Rs {sale.total_amount}")
    
    p.showPage()
    p.save()
    
    return response

@login_required
def export_sales_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sales.csv"'
    writer = csv.writer(response)
    writer.writerow(['Invoice ID', 'Date', 'Customer', 'Cashier', 'Subtotal', 'Tax', 'Discount', 'Total Amount'])
    
    sales = Sale.objects.filter(bakery=request.user.bakery).order_by('-date')
    for sale in sales:
        customer_name = sale.customer.name if sale.customer else 'Guest'
        writer.writerow([
            sale.id, 
            sale.date.strftime('%Y-%m-%d %H:%M'), 
            customer_name, 
            sale.cashier.username, 
            sale.subtotal, 
            sale.tax_amount, 
            f"{sale.discount_type}: {sale.discount_value}" if sale.discount_value else "None", 
            sale.total_amount
        ])
    return response


# ===================== PURCHASES =====================

@login_required
def purchase_list_view(request):
    purchases = Purchase.objects.filter(bakery=request.user.bakery).order_by('-date').select_related('supplier', 'inventory_item')
    return render(request, 'sales/purchase_list.html', {'purchases': purchases})


@login_required
def create_purchase_view(request):
    if not request.user.is_owner and request.user.role not in ['Manager', 'Inventory Clerk']:
        return redirect('purchase_list')

    if request.method == 'POST':
        form = PurchaseForm(request.POST, bakery=request.user.bakery)
        if form.is_valid():
            purchase = form.save(commit=False)
            purchase.bakery = request.user.bakery
            purchase.save()
            return redirect('purchase_list')
    else:
        form = PurchaseForm(bakery=request.user.bakery)

    return render(request, 'sales/purchase_form.html', {'form': form})


# ===================== SUPPLIERS =====================

@login_required
def supplier_list_view(request):
    suppliers = Supplier.objects.filter(bakery=request.user.bakery)
    return render(request, 'sales/supplier_list.html', {'suppliers': suppliers})


@login_required
def supplier_create_view(request):
    if not request.user.is_owner and request.user.role not in ['Manager']:
        return redirect('supplier_list')
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            supplier = form.save(commit=False)
            supplier.bakery = request.user.bakery
            supplier.save()
            return redirect('supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'sales/supplier_form.html', {'form': form, 'action': 'Add'})


@login_required
def supplier_edit_view(request, pk):
    if not request.user.is_owner and request.user.role not in ['Manager']:
        return redirect('supplier_list')
    supplier = get_object_or_404(Supplier, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            return redirect('supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'sales/supplier_form.html', {'form': form, 'action': 'Edit'})


@login_required
def supplier_delete_view(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        supplier.delete()
        return redirect('supplier_list')
    return render(request, 'sales/supplier_confirm_delete.html', {'supplier': supplier})


# ===================== CUSTOMERS =====================

@login_required
def customer_list_view(request):
    customers = Customer.objects.filter(bakery=request.user.bakery)
    return render(request, 'sales/customer_list.html', {'customers': customers})


@login_required
def customer_create_view(request):
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            customer.bakery = request.user.bakery
            customer.save()
            return redirect('customer_list')
    else:
        form = CustomerForm()
    return render(request, 'sales/customer_form.html', {'form': form, 'action': 'Add'})


@login_required
def customer_edit_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            form.save()
            return redirect('customer_list')
    else:
        form = CustomerForm(instance=customer)
    return render(request, 'sales/customer_form.html', {'form': form, 'action': 'Edit'})


@login_required
def customer_delete_view(request, pk):
    customer = get_object_or_404(Customer, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        customer.delete()
        return redirect('customer_list')
    return render(request, 'sales/customer_confirm_delete.html', {'customer': customer})

# ==================== EXPENSES ====================

@login_required
def expense_list_view(request):
    expenses = Expense.objects.filter(bakery=request.user.bakery).order_by('-date')
    return render(request, 'sales/expense_list.html', {'expenses': expenses})

@login_required
def expense_create_view(request):
    if not request.user.is_owner:
        return redirect('dashboard')
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            expense = form.save(commit=False)
            expense.bakery = request.user.bakery
            expense.recorded_by = request.user
            expense.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm()
    return render(request, 'sales/expense_form.html', {'form': form, 'action': 'Add'})

@login_required
def expense_edit_view(request, pk):
    if not request.user.is_owner:
        return redirect('dashboard')
    expense = get_object_or_404(Expense, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('expense_list')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'sales/expense_form.html', {'form': form, 'action': 'Edit'})

@login_required
def expense_delete_view(request, pk):
    if not request.user.is_owner:
        return redirect('dashboard')
    expense = get_object_or_404(Expense, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        expense.delete()
        return redirect('expense_list')
    return render(request, 'sales/expense_confirm_delete.html', {'expense': expense})
