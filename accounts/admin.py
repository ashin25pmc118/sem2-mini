from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Bakery

class CustomUserAdmin(UserAdmin):
    model = User
    fieldsets = UserAdmin.fieldsets + (
        ('Bakery Info', {'fields': ('bakery', 'is_owner', 'role')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Bakery Info', {'fields': ('bakery', 'is_owner', 'role')}),
    )
    list_display = ['username', 'email', 'is_owner', 'role', 'bakery', 'is_staff']

admin.site.register(User, CustomUserAdmin)
admin.site.register(Bakery)
