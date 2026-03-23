import random
from decimal import Decimal
from django.core.management.base import BaseCommand
from accounts.models import Bakery
from store.models import ProductCategory, Product

class Command(BaseCommand):
    help = 'Populate database with sample bakery categories and products'

    def handle(self, *args, **kwargs):
        bakery = Bakery.objects.first()
        if not bakery:
            self.stdout.write(self.style.ERROR('No bakery found! Please register a bakery account first via the UI.'))
            return

        categories = {
            'Artisan Breads': [
                ('Classic Sourdough Loaf', 250.00, 80.00, 'nos'),
                ('French Baguette', 150.00, 40.00, 'nos'),
                ('Whole Wheat Multigrain', 180.00, 60.00, 'nos'),
                ('Focaccia with Olives', 200.00, 70.00, 'nos'),
            ],
            'Cakes & Celebration': [
                ('Chocolate Truffle Cake (1kg)', 1200.00, 450.00, 'nos'),
                ('Pineapple Fresh Cream', 800.00, 300.00, 'nos'),
                ('Red Velvet Cheesecake Slice', 250.00, 90.00, 'nos'),
                ('Black Forest Gateau', 900.00, 350.00, 'nos'),
            ],
            'Pastries & Viennoiserie': [
                ('Butter Croissant', 120.00, 40.00, 'nos'),
                ('Pain au Chocolat', 150.00, 50.00, 'nos'),
                ('Almond Danish', 160.00, 55.00, 'nos'),
                ('Fruit Tart', 180.00, 60.00, 'nos'),
                ('Cinnamon Roll', 140.00, 45.00, 'nos'),
            ],
            'Cookies & Biscuits': [
                ('Choco Chip Cookie (Pack of 6)', 200.00, 70.00, 'nos'),
                ('Oatmeal Raisin Cookies', 180.00, 60.00, 'nos'),
                ('Butter Melting Moments', 250.00, 80.00, 'nos'),
                ('Assorted Macarons (Box of 5)', 450.00, 150.00, 'nos'),
            ],
            'Beverages': [
                ('Hot Cappuccino', 180.00, 40.00, 'nos'),
                ('Iced Americano', 150.00, 30.00, 'nos'),
                ('Premium Hot Chocolate', 220.00, 70.00, 'nos'),
                ('Fresh Orange Juice', 160.00, 60.00, 'nos'),
            ]
        }

        created_cats = 0
        created_prods = 0

        for cat_name, products in categories.items():
            cat, created = ProductCategory.objects.get_or_create(bakery=bakery, name=cat_name)
            if created:
                created_cats += 1
            
            for prod_name, sell, cost, unit in products:
                prod, p_created = Product.objects.get_or_create(
                    bakery=bakery,
                    name=prod_name,
                    defaults={
                        'category': cat,
                        'cost_price': cost,
                        'selling_price': sell,
                        'tax_percentage': 5.0,
                        'stock_quantity': Decimal(random.randint(15, 60)),
                        'unit': unit,
                        'low_stock_alert': 10.0
                    }
                )
                if p_created:
                    created_prods += 1
                    
        self.stdout.write(self.style.SUCCESS(f'Successfully added {created_cats} categories and {created_prods} products to {bakery.name}!'))
