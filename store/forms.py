from django import forms
from .models import Product, InventoryItem, ProductCategory, ProductPurchase, Batch, WastageLog

class ProductCategoryForm(forms.ModelForm):
    class Meta:
        model = ProductCategory
        fields = ['name', 'image']

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'category', 'image', 'unit', 'cost_price', 'selling_price',
                  'tax_percentage', 'stock_quantity', 'low_stock_alert', 'is_active',
                  'enable_packet_selling', 'packet_size', 'packet_label', 'packet_selling_price']

    def __init__(self, *args, bakery=None, **kwargs):
        super().__init__(*args, **kwargs)
        if bakery:
            self.fields['category'].queryset = bakery.product_categories.all()

class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['name', 'quantity', 'unit', 'low_stock_alert_level']

class ProductPurchaseForm(forms.ModelForm):
    class Meta:
        model = ProductPurchase
        fields = ['product', 'quantity', 'purchase_price', 'supplier_name', 'invoice_number', 'note']

    def __init__(self, *args, bakery=None, **kwargs):
        super().__init__(*args, **kwargs)
        if bakery:
            self.fields['product'].queryset = Product.objects.filter(bakery=bakery, is_active=True)

class WastageLogForm(forms.ModelForm):
    class Meta:
        model = WastageLog
        fields = ['product', 'inventory_item', 'batch', 'quantity', 'reason']

    def __init__(self, *args, bakery=None, **kwargs):
        super().__init__(*args, **kwargs)
        if bakery:
            self.fields['product'].queryset = Product.objects.filter(bakery=bakery, is_active=True)
            self.fields['inventory_item'].queryset = InventoryItem.objects.filter(bakery=bakery, is_active=True)
            self.fields['batch'].queryset = Batch.objects.filter(bakery=bakery, is_active=True)
