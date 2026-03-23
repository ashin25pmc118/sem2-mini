from django.contrib import admin
from .models import Sale, SaleItem, Purchase

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1

class SaleAdmin(admin.ModelAdmin):
    inlines = [SaleItemInline]

admin.site.register(Sale, SaleAdmin)
admin.site.register(Purchase)
