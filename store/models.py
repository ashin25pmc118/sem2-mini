from django.db import models
from accounts.models import Bakery

class ProductCategory(models.Model):
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='product_categories')
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Product Categories"

    def __str__(self):
        return self.name

class Product(models.Model):
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=200)
    category = models.ForeignKey(ProductCategory, on_delete=models.SET_NULL, null=True, related_name='products')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    
    UNIT_CHOICES = [
        ('nos', 'Numbers (Nos)'),
        ('ml', 'Milliliters (ml)'),
        ('ltr', 'Liters (Ltr)'),
        ('g', 'Grams (g)'),
        ('kg', 'Kilograms (kg)'),
    ]
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='nos')
    
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    margin = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Auto-calculated")
    margin_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00, help_text="Auto-calculated %")
    
    TAX_CHOICES = [(0.0, '0%'), (5.0, '5%'), (12.0, '12%'), (18.0, '18%'), (28.0, '28%')]
    tax_percentage = models.DecimalField(max_digits=4, decimal_places=1, choices=TAX_CHOICES, default=0.0)
    
    stock_quantity = models.IntegerField(default=0, help_text="Current stock on hand (in base unit)")
    low_stock_alert = models.IntegerField(default=5, help_text="Alert when stock falls below this")
    
    # Multi-unit selling
    enable_packet_selling = models.BooleanField(default=False, help_text="Allow selling in packets")
    packet_size = models.IntegerField(default=1, help_text="How many nos per packet (e.g., 10 candies = 1 pkt)")
    packet_label = models.CharField(max_length=30, default='Packet', help_text="Label for the packet unit (e.g., Pkt, Box, Dozen)")
    packet_selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text="Price when selling a full packet")
    
    is_active = models.BooleanField(default=True)

    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.low_stock_alert

    def save(self, *args, **kwargs):
        # Auto calculate margin and margin percentage before saving
        if self.selling_price and self.cost_price is not None:
            self.margin = self.selling_price - self.cost_price
            if self.cost_price > 0:
                self.margin_percentage = (self.margin / self.cost_price) * 100
            else:
                # If cost is 0, margin is 100% technically (pure profit), handling div by zero.
                self.margin_percentage = 100.00 if self.selling_price > 0 else 0.00
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class InventoryItem(models.Model):
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='inventory')
    name = models.CharField(max_length=200)
    quantity = models.IntegerField(default=0)
    unit = models.CharField(max_length=50, help_text="e.g., kg, liters, units")
    low_stock_alert_level = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True)

    @property
    def is_low_stock(self):
        return self.quantity <= self.low_stock_alert_level

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

class Batch(models.Model):
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='batches')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='batches', null=True, blank=True)
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='batches', null=True, blank=True)
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()
    initial_quantity = models.IntegerField()
    current_quantity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        item_name = self.product.name if self.product else (self.inventory_item.name if self.inventory_item else "Unknown")
        return f"{item_name} - {self.batch_number} (Exp: {self.expiry_date})"

class WastageLog(models.Model):
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='wastage_logs')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wastage_logs', null=True, blank=True)
    inventory_item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='wastage_logs', null=True, blank=True)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True, blank=True, related_name='wastage_logs')
    quantity = models.IntegerField()
    reason = models.CharField(max_length=255, help_text="e.g., Expired, Damaged, Stale")
    logged_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True)
    logged_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        item = self.product or self.inventory_item
        return f"Wastage: {self.quantity} of {item} - {self.reason}"


class StockMovement(models.Model):
    """Audit log: every change to a product's stock_quantity is recorded here."""
    MOVEMENT_TYPES = [
        ('IN',  'Stock In'),     # purchase / manual adjustment
        ('OUT', 'Stock Out'),    # sale
        ('ADJ', 'Adjustment'),   # manual correction
    ]
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='stock_movements')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='stock_movements')
    movement_type = models.CharField(max_length=5, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    reference = models.CharField(max_length=200, blank=True, help_text="e.g. Sale #5 / Purchase #3")
    note = models.TextField(blank=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_movement_type_display()} {self.quantity} × {self.product.name} ({self.date:%d %b %Y})"


class ProductPurchase(models.Model):
    """Buy finished products from a supplier — auto-adds to product stock_quantity."""
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, related_name='product_purchases')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='purchases')
    quantity = models.IntegerField()
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price paid per unit")
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, editable=False, default=0)
    supplier_name = models.CharField(max_length=200, blank=True)
    invoice_number = models.CharField(max_length=100, blank=True)
    date = models.DateTimeField(auto_now_add=True)
    note = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        self.total_cost = self.quantity * self.purchase_price
        super().save(*args, **kwargs)
        if is_new:
            # Add to product stock
            self.product.stock_quantity += self.quantity
            self.product.save(update_fields=['stock_quantity'])
            # Record stock movement
            StockMovement.objects.create(
                bakery=self.bakery,
                product=self.product,
                movement_type='IN',
                quantity=self.quantity,
                reference=f"Purchase #{self.pk} from {self.supplier_name or 'Supplier'}",
            )

    def __str__(self):
        return f"Purchase {self.quantity} × {self.product.name} @ ₹{self.purchase_price}"
