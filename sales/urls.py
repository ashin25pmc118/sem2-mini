from django.urls import path
from sales import views

urlpatterns = [
    # POS & Sales
    path('pos/', views.pos_billing_view, name='pos_billing'),
    path('history/', views.sales_list_view, name='sales_list'),
    path('history/<int:sale_id>/pdf/', views.generate_invoice_pdf, name='generate_invoice_pdf'),
    path('history/export/csv/', views.export_sales_csv, name='export_sales_csv'),

    # Purchases
    path('purchases/', views.purchase_list_view, name='purchase_list'),
    path('purchases/add/', views.create_purchase_view, name='purchase_create'),

    # Suppliers
    path('suppliers/', views.supplier_list_view, name='supplier_list'),
    path('suppliers/add/', views.supplier_create_view, name='supplier_create'),
    path('suppliers/<int:pk>/edit/', views.supplier_edit_view, name='supplier_edit'),
    path('suppliers/<int:pk>/delete/', views.supplier_delete_view, name='supplier_delete'),

    # Customers
    path('customers/', views.customer_list_view, name='customer_list'),
    path('customers/add/', views.customer_create_view, name='customer_create'),
    path('customers/<int:pk>/edit/', views.customer_edit_view, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete_view, name='customer_delete'),
]
