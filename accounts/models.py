import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser

class Bakery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    address = models.TextField()
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class User(AbstractUser):
    ROLE_CHOICES = (
        ('Owner', 'Owner'),
        ('Manager', 'Manager'),
        ('Cashier', 'Cashier'),
        ('Inventory Clerk', 'Inventory Clerk'),
    )
    
    bakery = models.ForeignKey(Bakery, on_delete=models.CASCADE, null=True, blank=True, related_name='staff')
    is_owner = models.BooleanField(default=False)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, blank=True, null=True)

    def __str__(self):
        return f"{self.username} - {self.role or 'Admin'}"
