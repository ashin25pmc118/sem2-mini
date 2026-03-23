from django import forms
from .models import Sale, SaleItem, Purchase, Supplier, Customer
from store.models import Product, InventoryItem


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['name', 'phone', 'email', 'address', 'payment_preference']


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_number', 'email', 'address']


class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['payment_method']


class SaleItemForm(forms.ModelForm):
    class Meta:
        model = SaleItem
        fields = ['product', 'quantity']

    def __init__(self, *args, bakery=None, **kwargs):
        super().__init__(*args, **kwargs)
        if bakery:
            self.fields['product'].queryset = Product.objects.filter(bakery=bakery, is_active=True)


class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'inventory_item', 'quantity_added', 'total_cost', 'transportation_charge', 'invoice_number']

    def __init__(self, *args, bakery=None, **kwargs):
        super().__init__(*args, **kwargs)
        if bakery:
            self.fields['inventory_item'].queryset = InventoryItem.objects.filter(bakery=bakery)
            self.fields['supplier'].queryset = Supplier.objects.filter(bakery=bakery)
            self.fields['supplier'].required = False
