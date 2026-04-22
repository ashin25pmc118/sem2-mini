from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
from store.models import Product, InventoryItem
from accounts.models import CustomUser

class Command(BaseCommand):
    help = 'Sends email alerts for low stock items'

    def handle(self, *args, **kwargs):
        # Find low stock products
        products = Product.objects.filter(is_active=True)
        low_products = [p for p in products if p.is_low_stock]
        
        items = InventoryItem.objects.filter(is_active=True)
        low_items = [i for i in items if hasattr(i, 'is_low_stock') and i.is_low_stock]
        
        if not low_products and not low_items:
            self.stdout.write(self.style.SUCCESS('No low stock items found.'))
            return
            
        subject = 'Low Stock Alert - ManageNest'
        message = 'The following items are running low on stock:\n\n'
        
        if low_products:
            message += '--- Products ---\n'
            for p in low_products:
                message += f'- {p.name}: {p.stock_quantity} (Alert at {p.low_stock_alert})\n'
                
        if low_items:
            message += '\n--- Raw Materials ---\n'
            for i in low_items:
                message += f'- {i.name}: {i.quantity} (Alert at {i.low_stock_alert_level})\n'
                
        admin_emails = [admin.email for admin in CustomUser.objects.filter(is_superuser=True, is_active=True) if admin.email]
        
        if not admin_emails:
            self.stdout.write(self.style.WARNING('No admin emails configured. Cannot send alerts.'))
            return

        send_mail(
            subject,
            message,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@bakerymate.com'),
            admin_emails,
            fail_silently=True,
        )
        
        self.stdout.write(self.style.SUCCESS(f'Low stock alerts sent to {len(admin_emails)} admins.'))
