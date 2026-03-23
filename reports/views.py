from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, F
from django.utils import timezone
from sales.models import Sale, Purchase, Expense
from store.models import ProductPurchase

@login_required
def profit_loss_report(request):
    bakery = request.user.bakery
    today = timezone.localdate()
    
    # Revenue
    sales = Sale.objects.filter(bakery=bakery)
    total_revenue = sales.aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Raw Materials
    raw_materials = Purchase.objects.filter(bakery=bakery).aggregate(cost=Sum('total_cost'), trans=Sum('transportation_charge'))
    rm_cost = (raw_materials['cost'] or 0) + (raw_materials['trans'] or 0)
    
    # Finished Products
    product_purchases = ProductPurchase.objects.filter(bakery=bakery).aggregate(total=Sum('total_cost'))['total'] or 0
    
    total_purchases = rm_cost + product_purchases
    
    # General Expenses
    general_expenses = Expense.objects.filter(bakery=bakery).aggregate(total=Sum('amount'))['total'] or 0

    net_profit = total_revenue - (total_purchases + general_expenses)
    
    context = {
        'total_revenue': total_revenue,
        'total_purchases': total_purchases,
        'rm_cost': rm_cost,
        'product_purchases': product_purchases,
        'general_expenses': general_expenses,
        'net_profit': net_profit,
    }
    return render(request, 'reports/profit_loss.html', context)

@login_required
def sales_report(request):
    bakery = request.user.bakery
    sales = Sale.objects.filter(bakery=bakery).order_by('-date')
    total_sales_amount = sales.aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        'sales': sales,
        'total_sales_amount': total_sales_amount,
    }
    return render(request, 'reports/sales_report.html', context)

@login_required
def purchases_report(request):
    bakery = request.user.bakery
    raw_materials = Purchase.objects.filter(bakery=bakery).order_by('-date')
    product_purchases = ProductPurchase.objects.filter(bakery=bakery).order_by('-date')
    
    total_rm_cost = sum([p.total_cost + (p.transportation_charge or 0) for p in raw_materials])
    total_pp_cost = sum([p.total_cost for p in product_purchases])
    
    total_purchases = total_rm_cost + total_pp_cost

    context = {
        'raw_materials': raw_materials,
        'product_purchases': product_purchases,
        'total_purchases': total_purchases,
        'total_rm_cost': total_rm_cost,
        'total_pp_cost': total_pp_cost,
    }
    return render(request, 'reports/purchases_report.html', context)

@login_required
def expenses_report(request):
    bakery = request.user.bakery
    expenses = Expense.objects.filter(bakery=bakery).order_by('-date')
    total_expenses = expenses.aggregate(total=Sum('amount'))['total'] or 0

    context = {
        'expenses': expenses,
        'total_expenses': total_expenses,
    }
    return render(request, 'reports/expenses_report.html', context)
