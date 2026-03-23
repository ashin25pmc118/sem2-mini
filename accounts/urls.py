from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path('', RedirectView.as_view(url='/login/', permanent=False), name='index'),
    path('register/', views.bakery_registration_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('staff/add/', views.staff_creation_view, name='create_staff'),
    path('staff/', views.staff_list_view, name='staff_list'),
    path('staff/edit/<int:pk>/', views.staff_edit_view, name='edit_staff'),
    path('staff/delete/<int:pk>/', views.staff_delete_view, name='delete_staff'),
]
