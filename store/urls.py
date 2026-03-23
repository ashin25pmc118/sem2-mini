from django.urls import path
from store import views

urlpatterns = [
    # Products & Categories
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_create, name='product_create'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('categories/add/', views.category_create, name='category_create'),

    # Raw Material Inventory
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/add/', views.inventory_create, name='inventory_create'),
    path('inventory/export/csv/', views.export_inventory_csv, name='export_inventory_csv'),

    # Stock Module
    path('stock/', views.stock_dashboard, name='stock_dashboard'),
    path('stock/history/', views.stock_history, name='stock_history'),
    path('stock/history/<int:product_id>/', views.stock_history, name='stock_history_product'),
    path('stock/adjust/<int:pk>/', views.stock_adjust, name='stock_adjust'),
    path('wastage/', views.wastage_list, name='wastage_list'),
    path('wastage/add/', views.wastage_create, name='wastage_create'),

    # Product Purchase Module
    path('product-purchases/', views.product_purchase_list, name='product_purchase_list'),
    path('product-purchases/add/', views.product_purchase_create, name='product_purchase_create'),
    
    # API endpoints
    path('api/products/search/', views.api_search_products, name='api_search_products'),
]
