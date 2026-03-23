import json
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import Product, InventoryItem, ProductCategory, StockMovement, ProductPurchase, WastageLog
from .forms import ProductForm, InventoryItemForm, ProductCategoryForm, ProductPurchaseForm, WastageLogForm
import csv
from django.http import HttpResponse

# ===================== PRODUCTS =====================

@login_required
def product_list(request):
    products = Product.objects.filter(bakery=request.user.bakery).select_related('category')
    return render(request, 'store/product_list.html', {'products': products})

@login_required
def product_create(request):
    if not request.user.is_owner:
        return redirect('product_list')
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, bakery=request.user.bakery)
        if form.is_valid():
            product = form.save(commit=False)
            product.bakery = request.user.bakery
            product.save()
            return redirect('product_list')
    else:
        form = ProductForm(bakery=request.user.bakery)
    return render(request, 'store/product_form.html', {'form': form, 'action': 'Add'})

@login_required
def product_edit(request, pk):
    if not request.user.is_owner:
        return redirect('product_list')
    product = get_object_or_404(Product, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product, bakery=request.user.bakery)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product, bakery=request.user.bakery)
    return render(request, 'store/product_form.html', {'form': form, 'action': 'Edit'})

@login_required
def product_delete(request, pk):
    if not request.user.is_owner:
        return redirect('product_list')
    product = get_object_or_404(Product, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')
    return render(request, 'store/product_confirm_delete.html', {'product': product})

@login_required
def category_create(request):
    if not request.user.is_owner:
        return redirect('product_list')
    if request.method == 'POST':
        form = ProductCategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save(commit=False)
            category.bakery = request.user.bakery
            category.save()
            return redirect('product_create')
    else:
        form = ProductCategoryForm()
    return render(request, 'store/category_form.html', {'form': form})

# ===================== INVENTORY (RAW MATERIALS) =====================

@login_required
def inventory_list(request):
    items = InventoryItem.objects.filter(bakery=request.user.bakery)
    return render(request, 'store/inventory_list.html', {'items': items})

@login_required
def inventory_create(request):
    if not request.user.is_owner:
        return redirect('inventory_list')
    if request.method == 'POST':
        form = InventoryItemForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.bakery = request.user.bakery
            item.save()
            return redirect('inventory_list')
    else:
        form = InventoryItemForm()
    return render(request, 'store/inventory_form.html', {'form': form, 'action': 'Add'})

@login_required
def export_inventory_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="inventory.csv"'
    writer = csv.writer(response)
    writer.writerow(['Item Name', 'Quantity', 'Unit', 'Alert Level', 'Low Stock'])
    
    items = InventoryItem.objects.filter(bakery=request.user.bakery, is_active=True)
    for i in items:
        writer.writerow([
            i.name, 
            i.quantity, 
            i.get_unit_display() if hasattr(i, 'get_unit_display') else getattr(i, 'unit', ''), 
            i.low_stock_alert_level,
            "Yes" if hasattr(i, 'is_low_stock') and i.is_low_stock else "No"
        ])
    return response

# ===================== STOCK MODULE =====================

@login_required
def wastage_list(request):
    logs = WastageLog.objects.filter(bakery=request.user.bakery).order_by('-logged_at')
    return render(request, 'store/wastage_list.html', {'logs': logs})

@login_required
def wastage_create(request):
    if not request.user.is_owner:
        return redirect('wastage_list')
    if request.method == 'POST':
        form = WastageLogForm(request.POST, bakery=request.user.bakery)
        if form.is_valid():
            wastage = form.save(commit=False)
            wastage.bakery = request.user.bakery
            wastage.logged_by = request.user
            try:
                with transaction.atomic():
                    if wastage.batch:
                        wastage.batch.current_quantity -= wastage.quantity
                        wastage.batch.save()
                    if wastage.product:
                        wastage.product.stock_quantity -= wastage.quantity
                        wastage.product.save()
                    elif wastage.inventory_item:
                        wastage.inventory_item.quantity -= wastage.quantity
                        wastage.inventory_item.save()
                    wastage.save()
            except Exception:
                pass
            return redirect('wastage_list')
    else:
        form = WastageLogForm(bakery=request.user.bakery)
    return render(request, 'store/wastage_form.html', {'form': form, 'action': 'Log Wastage'})

@login_required
def stock_dashboard(request):
    """Overview of all product stock levels with low-stock alerts."""
    bakery = request.user.bakery
    products = Product.objects.filter(bakery=bakery, is_active=True).select_related('category').order_by('name')
    low_stock = [p for p in products if p.is_low_stock]
    return render(request, 'store/stock_dashboard.html', {
        'products': products,
        'low_stock': low_stock,
    })

@login_required
def stock_history(request, product_id=None):
    """Full movement history — optionally filtered to one product."""
    bakery = request.user.bakery
    movements = StockMovement.objects.filter(bakery=bakery).select_related('product').order_by('-date')
    product = None
    if product_id:
        product = get_object_or_404(Product, pk=product_id, bakery=bakery)
        movements = movements.filter(product=product)
    return render(request, 'store/stock_history.html', {
        'movements': movements,
        'product': product,
        'products': Product.objects.filter(bakery=bakery, is_active=True),
    })

@login_required
def stock_adjust(request, pk):
    """Manually adjust stock for a product (ADJ movement type)."""
    if not request.user.is_owner:
        return redirect('stock_dashboard')
    product = get_object_or_404(Product, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        adj_qty = request.POST.get('adjust_quantity', 0)
        adj_unit = request.POST.get('adjust_unit', 'base')
        note = request.POST.get('note', '')
        try:
            adj_qty = float(adj_qty)
            
            if adj_unit == 'pkt' and product.enable_packet_selling:
                original_qty = adj_qty
                adj_qty = adj_qty * product.packet_size
                note_suffix = f"(Adjusted in packets: {original_qty} {product.packet_label})"
                note = f"{note} {note_suffix}".strip()
                
            product.stock_quantity += adj_qty
            product.save(update_fields=['stock_quantity'])
            StockMovement.objects.create(
                bakery=request.user.bakery,
                product=product,
                movement_type='ADJ',
                quantity=adj_qty,
                note=note,
                reference=f"Manual adjustment by {request.user.username}",
            )
        except (ValueError, TypeError):
            pass
        return redirect('stock_dashboard')
    return render(request, 'store/stock_adjust.html', {'product': product})

# ===================== PRODUCT PURCHASE =====================

@login_required
def product_purchase_list(request):
    purchases = ProductPurchase.objects.filter(bakery=request.user.bakery).select_related('product').order_by('-date')
    return render(request, 'store/product_purchase_list.html', {'purchases': purchases})

@login_required
def product_purchase_create(request):
    if not request.user.is_owner:
        return redirect('product_purchase_list')
    bakery = request.user.bakery
    
    if request.method == 'POST':
        supplier_name = request.POST.get('supplier_name', '')
        invoice_number = request.POST.get('invoice_number', '')
        note = request.POST.get('note', '')
        items_json = request.POST.get('items_json', '[]')
        
        try:
            items = json.loads(items_json)
            with transaction.atomic():
                for item in items:
                    product_id = item.get('product_id')
                    quantity = float(item.get('quantity', 0))
                    purchase_price = float(item.get('purchase_price', 0))
                    unit_type = item.get('unit_type', 'base')
                    
                    if not product_id or quantity <= 0:
                        continue
                        
                    product = get_object_or_404(Product, pk=product_id, bakery=bakery)
                    
                    if unit_type == 'pkt' and product.enable_packet_selling:
                        quantity = quantity * product.packet_size
                        purchase_price = purchase_price / product.packet_size
                    
                    purchase = ProductPurchase.objects.create(
                        bakery=bakery,
                        product=product,
                        quantity=quantity,
                        purchase_price=purchase_price,
                        supplier_name=supplier_name,
                        invoice_number=invoice_number,
                        note=note
                    )
                     # Note: ProductPurchase.save() automatically triggers stock increment 
                     # and creates the StockMovement history record.
            
            return redirect('product_purchase_list')
        except Exception as e:
            # Handle JSON parse errors or invalid data gracefully
            # In a real app we'd add messages, but here we just re-render
            pass

    # Provide an unbound form just so we can render the drop-downs easily
    form = ProductPurchaseForm(bakery=bakery)

    # Calculate expected next Purchase ID
    from django.db.models import Max
    max_id = ProductPurchase.objects.all().aggregate(Max('id'))['id__max']
    expected_purchase_id = (max_id or 0) + 1

    # Pass cost prices and units so template JS can auto-fill and display them
    active_products = Product.objects.filter(bakery=bakery, is_active=True)
    cost_prices = {str(p.id): float(p.cost_price) for p in active_products}
    product_units = {str(p.id): p.get_unit_display() for p in active_products}
    product_names = {str(p.id): str(p.name) for p in active_products}
    
    product_packet_selling = {str(p.id): p.enable_packet_selling for p in active_products}
    product_packet_labels = {str(p.id): str(p.packet_label) if p.packet_label else 'Packet' for p in active_products}
    product_packet_sizes = {str(p.id): float(p.packet_size) if p.packet_size else 1.0 for p in active_products}
    
    return render(request, 'store/product_purchase_form.html', {
        'form': form,
        'expected_purchase_id': expected_purchase_id,
        'cost_prices_json': json.dumps(cost_prices),
        'product_units_json': json.dumps(product_units),
        'product_names_json': json.dumps(product_names),
        'product_packet_selling_json': json.dumps(product_packet_selling),
        'product_packet_labels_json': json.dumps(product_packet_labels),
        'product_packet_sizes_json': json.dumps(product_packet_sizes),
    })

# ===================== API =====================

@login_required
def api_search_products(request):
    """
    API endpoint for dynamic product search (POS & Purchases).
    Matches query 'q' against Product Name or ID.
    Optional 'cat' filters by Category ID.
    """
    bakery = request.user.bakery
    q = request.GET.get('q', '').strip()
    cat = request.GET.get('cat', 'all')
    
    products = Product.objects.filter(bakery=bakery, is_active=True)
    
    if cat != 'all' and cat.isdigit():
        products = products.filter(category_id=int(cat))
        
    if q:
        if q.isdigit():
            # Match ID exactly or name partially
            products = products.filter(Q(id=int(q)) | Q(name__icontains=q))
        else:
            products = products.filter(name__icontains=q)
            
    # Limit to 30 items for speed
    products = products[:30]
    
    results = []
    for p in products:
        results.append({
            'id': p.id,
            'name': p.name,
            'selling_price': float(p.selling_price) if p.selling_price else 0.0,
            'cost_price': float(p.cost_price) if p.cost_price else 0.0,
            'stock': float(p.stock_quantity) if p.stock_quantity else 0.0,
            'unit': p.get_unit_display() if hasattr(p, 'get_unit_display') else getattr(p, 'unit', ''),
            'tax_percentage': float(p.tax_percentage) if p.tax_percentage else 0.0,
            'image': p.image.url if p.image and getattr(p.image, 'name', None) else None,
            'category_id': p.category_id,
            'enable_packet_selling': p.enable_packet_selling,
            'packet_size': p.packet_size,
            'packet_label': p.packet_label,
            'packet_selling_price': float(p.packet_selling_price) if p.packet_selling_price else 0.0,
        })
        
    return JsonResponse({'products': results})
