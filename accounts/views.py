from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from .forms import BakeryRegistrationForm, StaffCreationForm, StaffEditForm, BakeryEditForm, OwnerProfileEditForm
from .models import User, Bakery
from django.db import transaction
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
from sales.models import Sale, SaleItem
from store.models import Product, InventoryItem
import json

def bakery_registration_view(request):
    if request.method == 'POST':
        form = BakeryRegistrationForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Save bakery
                    bakery = form.save()
                    
                    # Create Owner user
                    owner = User.objects.create_user(
                        username=form.cleaned_data['owner_username'],
                        email=form.cleaned_data['owner_email'],
                        password=form.cleaned_data['owner_password'],
                        bakery=bakery,
                        is_owner=True,
                        role='Owner'
                    )
                    
                    # Log them in automatically
                    login(request, owner)
                    return redirect('dashboard')
            except Exception as e:
                # Handle unexpected DB or Integrity errors gracefully
                form.add_error(None, "An unexpected error occurred while setting up your bakery. Please try again or contact support.")
    else:
        form = BakeryRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def dashboard_view(request):
    bakery = request.user.bakery
    
    total_products = Product.objects.filter(bakery=bakery, is_active=True).count()
    total_sales = Sale.objects.filter(bakery=bakery).count()
    total_inventory = InventoryItem.objects.filter(bakery=bakery, is_active=True).count()
    
    today = timezone.now().date()
    today_revenue = Sale.objects.filter(bakery=bakery, date__date=today).aggregate(total=Sum('total_amount'))['total'] or 0
    month_revenue = Sale.objects.filter(bakery=bakery, date__year=today.year, date__month=today.month).aggregate(total=Sum('total_amount'))['total'] or 0
    
    recent_sales = Sale.objects.filter(bakery=bakery).order_by('-date')[:5]
    
    # 1. P&L Calculation (Revenue - Purchases - Transport)
    from sales.models import Purchase, Expense
    from store.models import ProductPurchase
    raw_materials = Purchase.objects.filter(bakery=bakery, date__year=today.year, date__month=today.month).aggregate(cost=Sum('total_cost'), trans=Sum('transportation_charge'))
    rm_cost = (raw_materials['cost'] or 0) + (raw_materials['trans'] or 0)
    
    product_purchases = ProductPurchase.objects.filter(bakery=bakery, date__year=today.year, date__month=today.month).aggregate(total=Sum('total_cost'))['total'] or 0
    
    # General Expenses
    general_expenses = Expense.objects.filter(bakery=bakery, date__year=today.year, date__month=today.month).aggregate(total=Sum('amount'))['total'] or 0

    profit_and_loss = month_revenue - (rm_cost + product_purchases + general_expenses)
    
    low_stock_qs = Product.objects.filter(bakery=bakery, is_active=True, stock_quantity__lte=F('low_stock_alert'))
    low_stock_items = low_stock_qs[:5]
    low_stock_count = low_stock_qs.count()

    sevendays_ago = today - timedelta(days=6)
    daily_sales = Sale.objects.filter(bakery=bakery, date__date__gte=sevendays_ago).annotate(
        day=TruncDate('date')
    ).values('day').annotate(
        daily_total=Sum('total_amount')
    ).order_by('day')
    
    days_labels = [(sevendays_ago + timedelta(days=i)).strftime('%b %d') for i in range(7)]
    sales_data_dict = {str(item['day']): float(item['daily_total']) for item in daily_sales}
    sales_data = [sales_data_dict.get(str(sevendays_ago + timedelta(days=i)), 0) for i in range(7)]

    top_products = SaleItem.objects.filter(sale__bakery=bakery).values('product__name').annotate(
        total_quantity=Sum('quantity')
    ).order_by('-total_quantity')[:5]

    top_product_labels = [item['product__name'] for item in top_products]
    top_product_data = [float(item['total_quantity']) for item in top_products]

    context = {
        'total_products': total_products,
        'total_sales': total_sales,
        'total_inventory': total_inventory,
        'today_revenue': today_revenue,
        'month_revenue': month_revenue,
        'profit_and_loss': profit_and_loss,
        'general_expenses': general_expenses,
        'recent_sales': recent_sales,
        'low_stock_items': low_stock_items,
        'low_stock_count': low_stock_count,
        'days_labels_json': json.dumps(days_labels),
        'sales_data_json': json.dumps(sales_data),
        'top_product_labels_json': json.dumps(top_product_labels),
        'top_product_data_json': json.dumps(top_product_data)
    }
    
    return render(request, 'accounts/dashboard.html', context)

@login_required
def staff_creation_view(request):
    if not request.user.is_owner:
        return redirect('dashboard') # Only owner can create staff
        
    if request.method == 'POST':
        form = StaffCreationForm(request.POST)
        if form.is_valid():
            # Pass bakery to the save method
            form.save(bakery=request.user.bakery)
            return redirect('staff_list')
    else:
        form = StaffCreationForm()
        
    return render(request, 'accounts/create_staff.html', {'form': form})

@login_required
def staff_list_view(request):
    if not request.user.is_owner:
        return redirect('dashboard')
    
    staff_members = User.objects.filter(bakery=request.user.bakery).exclude(id=request.user.id)
    return render(request, 'accounts/staff_list.html', {'staff_list': staff_members})

@login_required
def staff_edit_view(request, pk):
    if not request.user.is_owner:
        return redirect('dashboard')
        
    staff = get_object_or_404(User, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        form = StaffEditForm(request.POST, instance=staff)
        if form.is_valid():
            form.save()
            return redirect('staff_list')
    else:
        form = StaffEditForm(instance=staff)
        
    return render(request, 'accounts/staff_form.html', {'form': form, 'action': 'Edit', 'staff': staff})

@login_required
def staff_delete_view(request, pk):
    if not request.user.is_owner:
        return redirect('dashboard')
        
    staff = get_object_or_404(User, pk=pk, bakery=request.user.bakery)
    if request.method == 'POST':
        staff.delete()
        return redirect('staff_list')
        
    return render(request, 'accounts/staff_confirm_delete.html', {'staff': staff})

@login_required
def profile_edit_view(request):
    user = request.user
    
    if not user.is_owner:
        return redirect('dashboard')
        
    bakery = user.bakery
    
    if request.method == 'POST':
        user_form = OwnerProfileEditForm(request.POST, instance=user)
        bakery_form = BakeryEditForm(request.POST, instance=bakery)
        password_form = PasswordChangeForm(user, request.POST)
        
        # Check if user made changes to password fields
        password_changed = False
        if any(request.POST.get(f) for f in ['old_password', 'new_password1', 'new_password2']):
            password_changed = True

        if user_form.is_valid() and bakery_form.is_valid():
            if not password_changed or password_form.is_valid():
                user_form.save()
                bakery_form.save()
                if password_changed:
                    user = password_form.save()
                    update_session_auth_hash(request, user) # keeps user logged in
                messages.success(request, "Shop Settings saved successfully!")
                return redirect('profile_edit')
    else:
        user_form = OwnerProfileEditForm(instance=user)
        bakery_form = BakeryEditForm(instance=bakery)
        password_form = PasswordChangeForm(user)
        
    context = {
        'user_form': user_form,
        'bakery_form': bakery_form,
        'password_form': password_form,
    }
    return render(request, 'accounts/profile_edit.html', context)
