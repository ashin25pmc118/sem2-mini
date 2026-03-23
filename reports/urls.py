from django.urls import path
from . import views

urlpatterns = [
    path('profit-loss/', views.profit_loss_report, name='profit_loss_report'),
    path('sales/', views.sales_report, name='sales_report'),
    path('purchases/', views.purchases_report, name='purchases_report'),
    path('expenses/', views.expenses_report, name='expenses_report'),
]
