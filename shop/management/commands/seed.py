# shop/management/commands/seed.py
from django.core.management.base import BaseCommand
from shop.models import Category, Product

class Command(BaseCommand):
    help = 'Seed the database with sample categories and products'

    def handle(self, *args, **options):
        categories = [
            ('graphic-tees', 'Graphic Tees'),
            ('basic-tees', 'Basic Tees'),
            ('v-neck', 'V-Neck'),
            ('long-sleeve', 'Long Sleeve'),
            ('polo', 'Polo'),
        ]
        for slug, name in categories:
            cat, created = Category.objects.get_or_create(slug=slug, defaults={'name': name})
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category {name}'))

        # create a couple of products if none exist
        if Product.objects.count() == 0:
            cat = Category.objects.get(slug='graphic-tees')
            Product.objects.create(title='Sunset Graphic Tee', slug='sunset-graphic-tee',
                                   description='Bright sunset print on soft cotton.',
                                   price=19.99, category=cat)
            Product.objects.create(title='Retro Logo Tee', slug='retro-logo-tee',
                                   description='Retro logo for a classic look.', price=22.00, category=cat)
            self.stdout.write(self.style.SUCCESS('Created sample products'))
        else:
            self.stdout.write('Products already exist')
