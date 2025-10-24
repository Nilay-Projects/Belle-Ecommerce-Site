from django.contrib import admin
from django import forms
from .models import Category, Product,Customer_Table,CustomerOrder,Cosmetic,Jewellery,Bag,Shoes,ContactMessage,Wishlist, Cart, CartItem
from django.utils.html import format_html

@admin.register(Customer_Table)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('customer_id', 'first_name', 'last_name', 'email', 'phone', 'city', 'created')
    search_fields = ('first_name', 'last_name', 'email')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('category_id', 'name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


class ProductForm(forms.ModelForm):
    sizes = forms.MultipleChoiceField(
        choices=Product.SIZE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Select available sizes for this product'
    )
    colors = forms.MultipleChoiceField(
        choices=Product.COLOR_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text='Select available colors for this product'
    )

    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # initialize checkboxes from instance JSON lists
        if self.instance and getattr(self.instance, 'pk', None):
            self.fields['sizes'].initial = self.instance.sizes or []
            self.fields['colors'].initial = self.instance.colors or []

    def clean_sizes(self):
        return list(self.cleaned_data.get('sizes', []))

    def clean_colors(self):
        return list(self.cleaned_data.get('colors', []))

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.sizes = self.cleaned_data.get('sizes', [])
        instance.colors = self.cleaned_data.get('colors', [])
        if commit:
            instance.save()
            self.save_m2m()
        return instance


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = ('product_id', 'title', 'category','display_collections','price', 'available', 
                    'created','brand', 'display_sizes', 'display_colors')
    list_filter = ('available', 'created', 'updated')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'category__name')


@admin.register(CustomerOrder)
class CustomerOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id','customer_id', 'first_name', 'last_name', 'email', 'telephone', 'total_price', 'payment_method', 'created_at'
    )
    list_filter = ('payment_method', 'created_at', 'country', 'region_state')
    search_fields = ('first_name', 'last_name', 'email', 'telephone', 'city', 'postcode')
    readonly_fields = ('created_at', 'order_items_pretty')

    def order_items_pretty(self, obj):
        """Render order items as HTML table in admin detail"""
        if obj.order_items:
            html = '<table style="border:1px solid #ccc; border-collapse:collapse;">'
            html += '<tr><th style="border:1px solid #ccc;padding:5px;">Product Name</th>'
            html += '<th style="border:1px solid #ccc;padding:5px;">Price</th>'
            html += '<th style="border:1px solid #ccc;padding:5px;">Size</th>'
            html += '<th style="border:1px solid #ccc;padding:5px;">Qty</th>'
            html += '<th style="border:1px solid #ccc;padding:5px;">Subtotal</th></tr>'
            for item in obj.order_items:
                html += f'<tr>'
                html += f'<td style="border:1px solid #ccc;padding:5px;">{item.get("product_name")}</td>'
                html += f'<td style="border:1px solid #ccc;padding:5px;">${item.get("price")}</td>'
                html += f'<td style="border:1px solid #ccc;padding:5px;">{item.get("size")}</td>'
                html += f'<td style="border:1px solid #ccc;padding:5px;">{item.get("quantity")}</td>'
                html += f'<td style="border:1px solid #ccc;padding:5px;">${item.get("subtotal")}</td>'
                html += '</tr>'
            html += '</table>'
            return format_html(html)  # ✅ Render HTML safely
        return "-"
    order_items_pretty.short_description = "Order Items"

    fieldsets = (
        ('Customer Info', {
            'fields': (
                'first_name', 'last_name', 'email', 'telephone', 'company', 'address',
                'apartment', 'city', 'postcode', 'country', 'region_state'
            )
        }),
        ('Order Info', {
            'fields': ('payment_method', 'order_notes', 'total_price', 'order_items_pretty', 'created_at')
        }),
    )


@admin.register(Cosmetic)
class CosmeticAdmin(admin.ModelAdmin):
    list_display = ('cosmetic_product_id', 'name', 'brand', 'price', 'display_collections', 'short_desc')
    list_filter = ('brand',)
    search_fields = ('name', 'brand')

    def display_collections(self, obj):
        if not obj.collection:
            return "-"
        return ", ".join([dict(obj.COLLECTION_CHOICES).get(k, k) for k in obj.collection])
    display_collections.short_description = "Collections"


@admin.register(Jewellery)
class JewelleryAdmin(admin.ModelAdmin):
    list_display = ('jewellery_product_id', 'name', 'price', 'display_collections','short_desc')
    search_fields = ('name',)

    def display_collections(self, obj):
        if not obj.collection:
            return "-"
        return ", ".join([dict(obj.COLLECTION_CHOICES).get(k, k) for k in obj.collection])
    display_collections.short_description = "Collections"


@admin.register(Bag)
class BagAdmin(admin.ModelAdmin):
    list_display = ('bag_product_id', 'name', 'price', 'collection', 'desc')
    list_filter = ('collection',)
    search_fields = ('name', 'collection')


@admin.register(Shoes)
class ShoeAdmin(admin.ModelAdmin):
    list_display = ('shoes_product_id', 'name', 'price', 'collection', 'desc')
    list_filter = ('collection',)
    search_fields = ('name', 'collection')


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'subject', 'created_at', 'is_read')
    list_filter = ('is_read', 'created_at')
    search_fields = ('name', 'email', 'subject', 'message')
    readonly_fields = ('created_at',)
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer_id',
        'category',
        'item_product_id',
        'title',
        'price',
        'created_at',
    )
    

    def has_add_permission(self, request):
        """Prevent manual addition — wishlist items are added by users."""
        return False

    def has_change_permission(self, request, obj=None):
        """Keep read-only to preserve original wishlist entries."""
        return False




# from django.contrib import admin
# from .models import Cart, CartItem, Customer_Table  # adjust import path as needed


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('created', 'updated')
    fields = ('product_id', 'product_title', 'size', 'quantity', 'price', 'image_url', 'created', 'updated')
    can_delete = True


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'customer_email', 'item_count', 'created', 'updated')
    search_fields = ('customer__email', 'customer__first_name', 'customer__last_name')
    inlines = (CartItemInline,)
    readonly_fields = ('created', 'updated')
    actions = ('clear_selected_carts',)

    def customer_email(self, obj):
        return getattr(obj.customer, 'email', None)
    customer_email.short_description = 'Customer Email'

    def item_count(self, obj):
        return obj.items.aggregate(total=models.Sum('quantity'))['total'] or 0
    item_count.short_description = 'Total Items'

    def clear_selected_carts(self, request, queryset):
        """
        Admin action to clear selected carts (delete items but keep cart row).
        """
        for cart in queryset:
            cart.items.all().delete()
        self.message_user(request, f"Cleared items from {queryset.count()} carts.")
    clear_selected_carts.short_description = 'Clear items from selected carts (delete CartItem rows)'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product_id', 'product_title', 'size', 'quantity', 'price', 'created', 'updated')
    search_fields = ('product_title', 'cart__customer__email')
    list_filter = ('size',)
    readonly_fields = ('created', 'updated')
