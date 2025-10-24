# shop/cart.py
from decimal import Decimal
from .models import Product

class Cart:
    """Simple session-based shopping cart."""
    def __init__(self, request):
        # store session and cart dict from session
        self.session = request.session
        cart = self.session.get('cart')
        if not cart:
            # if no cart in session, create an empty one
            cart = self.session['cart'] = {}
        self.cart = cart

    def add(self, product, quantity=1, update_quantity=False):
        """Add product to cart or update quantity."""
        product_id = str(product.id)
        if product_id not in self.cart:
            # store quantity and price as strings to be JSON serializable
            self.cart[product_id] = {'quantity': 0, 'price': str(product.price)}
        if update_quantity:
            self.cart[product_id]['quantity'] = quantity
        else:
            self.cart[product_id]['quantity'] += quantity
        self.save()

    def save(self):
        self.session.modified = True  # mark session as changed

    def remove(self, product):
        """Remove a product from the cart."""
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """Iterate over cart items and attach the product instances."""
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        for product in products:
            item = self.cart[str(product.id)]
            item['product'] = product
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            yield item

    def __len__(self):
        """Count all items in cart (sum of quantities)."""
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        """Return total price as Decimal."""
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        # empty cart
        self.session['cart'] = {}
        self.save()
