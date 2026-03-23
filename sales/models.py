from django.db import models
from accounts.models import Bakery, User
from store.models import Product, InventoryItem


class Supplier(models.Model):
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='suppliers')
    name = models.CharField(max_length=200)
    contact_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.bakery.name})"


class Customer(models.Model):
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='customers')
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    PAYMENT_PREF = [('Cash','Cash'),('Card','Card'),('UPI','UPI'),('Credit','Credit')]
    payment_preference = models.CharField(max_length=20, choices=PAYMENT_PREF, default='Cash')

    def __str__(self):
        return f"{self.name} ({self.phone or self.email or 'No contact'})"


class Sale(models.Model):
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='sales')
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales_processed')
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    date = models.DateTimeField(auto_now_add=True)
    
    # Financial fields
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    DISCOUNT_TYPES = [('Flat', 'Flat'), ('Percentage', 'Percentage')]
    discount_type = models.CharField(max_length=15, choices=DISCOUNT_TYPES, blank=True, null=True)
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    PAYMENT_CHOICES = (
        ('Cash', 'Cash'),
        ('Card', 'Card'),
        ('UPI', 'UPI'),
    )
    payment_method = models.CharField(max_length=50, choices=PAYMENT_CHOICES, default='Cash')
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"Invoice #{self.id} - ₹{self.total_amount}"

class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    SELL_UNIT_CHOICES = [('nos', 'Nos'), ('pkt', 'Packet')]
    quantity = models.IntegerField(default=1)
    sell_unit = models.CharField(max_length=10, choices=SELL_UNIT_CHOICES, default='nos')
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        if not self.price_at_sale and self.product:
            self.price_at_sale = self.product.selling_price
        super().save(*args, **kwargs)
        # Auto-deduct product stock on every NEW sale item
        if is_new and self.product:
            # FIFO Batch Deduction
            from store.models import Batch
            batches = Batch.objects.filter(
                product=self.product, bakery=self.product.bakery, current_quantity__gt=0, is_active=True
            ).order_by('expiry_date')
            
            qty_to_deduct = self.quantity_in_nos
            for batch in batches:
                if qty_to_deduct <= 0:
                    break
                if batch.current_quantity >= qty_to_deduct:
                    batch.current_quantity -= qty_to_deduct
                    batch.save(update_fields=['current_quantity'])
                    qty_to_deduct = 0
                else:
                    qty_to_deduct -= batch.current_quantity
                    batch.current_quantity = 0
                    batch.save(update_fields=['current_quantity'])
            
            self.product.stock_quantity -= self.quantity_in_nos
            self.product.save(update_fields=['stock_quantity'])

    @property
    def quantity_in_nos(self):
        """Return the actual number of individual units this sale represents."""
        if self.sell_unit == 'pkt' and self.product and self.product.enable_packet_selling:
            return self.quantity * self.product.packet_size
        return self.quantity

    @property
    def subtotal(self):
        return self.quantity * self.price_at_sale

    def __str__(self):
        return f"{self.quantity}x {self.product.name} (Sale #{self.sale.id})"

class Purchase(models.Model):
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='purchases')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='purchases')
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='purchase_history')
    date = models.DateTimeField(auto_now_add=True)
    quantity_added = models.IntegerField()
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    transportation_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    invoice_number = models.CharField(max_length=100, blank=True, null=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        # Update current inventory stock when a new purchase happens
        if is_new:
            self.inventory_item.quantity += self.quantity_added
            self.inventory_item.save()

    def __str__(self):
        return f"Bought {self.quantity_added} {self.inventory_item.unit} of {self.inventory_item.name} for ${self.total_cost}"
