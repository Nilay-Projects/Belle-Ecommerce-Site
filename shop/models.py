from django.db import models
from django.urls import reverse
from multiselectfield import MultiSelectField

class Customer_Table(models.Model):
    customer_id = models.AutoField(primary_key=True)  # unique, auto-increment
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)  # store hashed password
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.first_name} {self.last_name}'
    

class Category(models.Model):
    category_id = models.AutoField(primary_key=True)   # 👈 Auto increment PK
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', args=[self.slug])

# ✅ Function to return default sizes
def default_sizes():
    return ['S', 'M', 'L', 'XL', 'XXL']

class Product(models.Model):
    product_id = models.AutoField(primary_key=True)
    category = models.ForeignKey('Category', related_name='products', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True)
    description = models.TextField(blank=True)

    # Sizes
    SIZE_CHOICES = [
        ('S', 'S'),
        ('M', 'M'),
        ('L', 'L'),
        ('XL', 'XL'),
        ('XXL', 'XXL'),
    ]
    sizes = models.JSONField(
        default=default_sizes,  # ✅ Use module-level function, not lambda
        blank=True,
        help_text='List of sizes, e.g. ["S","M","L"]'
    )

    # Colors
    COLOR_CHOICES = [
        ('Black', 'Black'),
        ('White', 'White'),
        ('Red', 'Red'),
        ('Blue', 'Blue'),
        ('Pink', 'Pink'),
        ('Green','Green'),
        ('Orange','Orange'),
        ('Yellow','Yellow'),
        ('Grey','Grey'),
        ('Brown','Brown'),
        ('Navy Blue','Navy Blue'),
        ('Other','Other')
    ]
    colors = models.JSONField(default=list, blank=True, help_text='List of colors, e.g. ["Black","Red"]')

    # Brands
    BRAND_CHOICES = [
        ('Zara', 'Zara'),
        ('Anthropologie', 'Anthropologie'),
        ('Free People', 'Free People'),
        ('Reformation', 'Reformation'),
        ('Banana Republic', 'Banana Republic'),
    ]
    brand = models.CharField(max_length=50, choices=BRAND_CHOICES, default='Zara')

    # New collection category
    COLLECTION_CHOICES = [
        ('Best_selling', 'Best Selling'),
        ('Trending', 'Trending'),
        ('Sale', 'Sale'),
    ]
  
    collection_cat = MultiSelectField(
        choices=COLLECTION_CHOICES,
        max_choices=3,   # optional, limit max number of selections
        max_length=50,
        blank=True,      # allows no selection
        help_text='Select collection categories'
    )

    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    hover_image = models.ImageField(upload_to='products/hover/', blank=True, null=True)
    available = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('product_detail', args=[self.slug])

    def is_size_available(self, size):
        return bool(size) and (size in (self.sizes or []))

    def is_color_available(self, color):
        return bool(color) and (color in (self.colors or []))

    def display_sizes(self):
        if not self.sizes:
            return "-"
        return ", ".join(self.sizes)
    display_sizes.short_description = "Sizes"

    def display_colors(self):
        if not self.colors:
            return "-"
        return ", ".join(self.colors)
    display_colors.short_description = "Colors"
    
    def display_collections(self):
        """Return human-readable collection names for admin list view"""
        if not self.collection_cat:
            return "-"
        # collection_cat is already a list
        return ", ".join([dict(self.COLLECTION_CHOICES).get(k, k) for k in self.collection_cat])

    display_collections.short_description = "Collections"

class Cart(models.Model):
    customer = models.OneToOneField('Customer_Table', on_delete=models.CASCADE, related_name='cart')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Cart of {self.customer.email}'

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product_id = models.IntegerField()                  # store product id (avoid FK migration pain)
    product_title = models.CharField(max_length=255, blank=True)
    image_url = models.CharField(max_length=500, blank=True)
    size = models.CharField(max_length=10, blank=True)  # normalized size like 'M', '' for none
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # unit price at time added
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('cart', 'product_id', 'size')

    def __str__(self):
        return f'{self.quantity} x {self.product_title or self.product_id} ({self.size})'



class CustomerOrder(models.Model):
    # Customer info
    customer_id = models.IntegerField(null=True, blank=True, help_text="Customer ID stored in session (request.session['customer_id'])")
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=20)
    company = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255)
    apartment = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=20)
    country = models.CharField(max_length=100)
    region_state = models.CharField(max_length=100)

    # Order info
    order_notes = models.TextField(blank=True)
    payment_method = models.CharField(max_length=50)
    order_items = models.JSONField()  # Store products as list of dicts
    total_price = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} by {self.first_name} {self.last_name}"


class Cosmetic(models.Model):
    cosmetic_product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='cosmetics/', blank=True, null=True)
    image_hover = models.ImageField(upload_to='cosmetics/hover/', blank=True, null=True)
    short_desc = models.TextField(blank=True, help_text="Short description of the product")

    # Collection Choices (checkbox / multiple selection)
    COLLECTION_CHOICES = [
        ('We_recommed', 'We_recommed'),
        ('Whats_new', 'Whats_new'),
        ('Best_offer', 'Best_offer'),
    ]
    collection = MultiSelectField(
        choices=COLLECTION_CHOICES,
        max_choices=3,
        max_length=50,
        blank=True,
        help_text='Select one or more collection categories'
    )

    # Brand Choices (single select dropdown)
    BRAND_CHOICES = [
        ("L'Oréal Paris", "L'Oréal Paris"),
        ('Maybelline', 'Maybelline'),
        ('MAC', 'MAC'),
        ('Huda Beauty', 'Huda Beauty'),
        ('Fenty Beauty', 'Fenty Beauty'),
    ]
    brand = models.CharField(max_length=50, choices=BRAND_CHOICES, default="L'Oréal Paris")

    def __str__(self):
        return self.name

class Jewellery(models.Model):
    jewellery_product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    image = models.ImageField(upload_to='jewellery/', blank=True, null=True)
    image_hover = models.ImageField(upload_to='jewellery/hover/', blank=True, null=True)
    short_desc = models.TextField(blank=True, help_text="Short description of the product")

    # Collection Choices (multi-select)
    COLLECTION_CHOICES = [
        ('Most_selling', 'Most Selling'),
        ('Trending', 'Trending'),
        ('Sale', 'Sale'),
    ]
    collection = MultiSelectField(
        choices=COLLECTION_CHOICES,
        max_choices=3,
        max_length=50,
        blank=True,
        help_text='Select one or more collection categories'
    )

    def __str__(self):
        return self.name


class Bag(models.Model):
    COLLECTION_CHOICES = [
        ('Most_Selling', 'Most Selling'),
        ('Trending', 'Trending'),
        ('Sale', 'Sale'),
    ]

    bag_product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    collection = models.CharField(max_length=50, choices=COLLECTION_CHOICES, blank=True, null=True)
    desc = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='bags/', blank=True, null=True)
    image_hover = models.ImageField(upload_to='bags/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Bag"
        verbose_name_plural = "Bags"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('bag_info', args=[str(self.bag_product_id)])


class Shoes(models.Model):
    COLLECTION_CHOICES = [
        ('Most_Selling', 'Most Selling'),
        ('Trending', 'Trending'),
        ('Sale', 'Sale'),
    ]

    shoes_product_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    collection = models.CharField(max_length=50, choices=COLLECTION_CHOICES, blank=True, null=True)
    desc = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='shoes/', blank=True, null=True)
    image_hover = models.ImageField(upload_to='shoes/hover/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Shoe"
        verbose_name_plural = "Shoes"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shoe_info', args=[str(self.shoe_product_id)])


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True, null=True)
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"

    def __str__(self):
        return f"{self.name} — {self.subject or 'No subject'} ({self.email})"


class Wishlist(models.Model):
    customer_id = models.IntegerField()  # from session
    category = models.CharField(max_length=50)  # e.g. 'product', 'cosmetic', 'jewellery', 'bag', 'shoe'
    item_product_id = models.IntegerField()
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    hover_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.title} - {self.customer_id}"
