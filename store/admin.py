from django.contrib import admin
from .models import ProductCategory, Product, InventoryItem

admin.site.register(ProductCategory)
admin.site.register(Product)
admin.site.register(InventoryItem)
