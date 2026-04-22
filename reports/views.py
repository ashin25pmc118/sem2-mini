from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from django.utils import timezone
from sales.models import Sale, Purchase, Expense
from store.models import ProductPurchase

@login_required
def profit_loss_report(request):
    bakery = request.user.bakery
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    sales = Sale.objects.filter(bakery=bakery)
    raw_materials_qs = Purchase.objects.filter(bakery=bakery)
    product_purchases_qs = ProductPurchase.objects.filter(bakery=bakery)
    expenses_qs = Expense.objects.filter(bakery=bakery)

    if start_date:
        sales = sales.filter(date__date__gte=start_date)
        raw_materials_qs = raw_materials_qs.filter(date__date__gte=start_date)
        product_purchases_qs = product_purchases_qs.filter(date__date__gte=start_date)
        expenses_qs = expenses_qs.filter(date__date__gte=start_date)
    if end_date:
        sales = sales.filter(date__date__lte=end_date)
        raw_materials_qs = raw_materials_qs.filter(date__date__lte=end_date)
        product_purchases_qs = product_purchases_qs.filter(date__date__lte=end_date)
        expenses_qs = expenses_qs.filter(date__date__lte=end_date)
    
    # Revenue
    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Raw Materials
    raw_materials = raw_materials_qs.aggregate(cost=Sum('total_cost'), trans=Sum('transportation_charge'))
    rm_cost = (raw_materials['cost'] or 0) + (raw_materials['trans'] or 0)
    
    # Finished Products
    product_purchases = product_purchases_qs.aggregate(total=Sum('total_cost'))['total'] or 0
    
    total_purchases = rm_cost + product_purchases
    
    # General Expenses
    general_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or 0

    net_profit = total_revenue - (total_purchases + general_expenses)
    
    context = {
        'total_revenue': total_revenue,
        'total_purchases': total_purchases,
        'rm_cost': rm_cost,
        'product_purchases': product_purchases,
        'general_expenses': general_expenses,
        'net_profit': net_profit,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/profit_loss.html', context)

@login_required
def sales_report(request):
    bakery = request.user.bakery
    sales = Sale.objects.filter(bakery=bakery).order_by('-date')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        sales = sales.filter(date__date__gte=start_date)
    if end_date:
        sales = sales.filter(date__date__lte=end_date)

    total_sales_amount = sales.aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        'sales': sales,
        'total_sales_amount': total_sales_amount,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/sales_report.html', context)

@login_required
def purchases_report(request):
    bakery = request.user.bakery
    raw_materials = Purchase.objects.filter(bakery=bakery).order_by('-date')
    product_purchases = ProductPurchase.objects.filter(bakery=bakery).order_by('-date')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        raw_materials = raw_materials.filter(date__date__gte=start_date)
        product_purchases = product_purchases.filter(date__date__gte=start_date)
    if end_date:
        raw_materials = raw_materials.filter(date__date__lte=end_date)
        product_purchases = product_purchases.filter(date__date__lte=end_date)

    total_rm_cost = sum([p.total_cost + (p.transportation_charge or 0) for p in raw_materials])
    total_pp_cost = sum([p.total_cost for p in product_purchases])
    
    total_purchases = total_rm_cost + total_pp_cost

    context = {
        'raw_materials': raw_materials,
        'product_purchases': product_purchases,
        'total_purchases': total_purchases,
        'total_rm_cost': total_rm_cost,
        'total_pp_cost': total_pp_cost,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/purchases_report.html', context)

@login_required
def expenses_report(request):
    bakery = request.user.bakery
    expenses = Expense.objects.filter(bakery=bakery).order_by('-date')

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if start_date:
        expenses = expenses.filter(date__date__gte=start_date)
    if end_date:
        expenses = expenses.filter(date__date__lte=end_date)

    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'reports/expenses_report.html', context)
