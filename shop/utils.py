# shop/utils.py
from decimal import Decimal, ROUND_HALF_UP
from .models import Cart, CartItem, Customer_Table, Product

def get_or_create_cart_for_customer(customer):
    cart, _ = Cart.objects.get_or_create(customer=customer)
    return cart

def sync_session_item_to_db(customer, key, item):
    """
    Merge one session item into DB cart (increments quantity).
    item is a dict with keys product_id, name, price (string), quantity, image, size.
    """
    cart = get_or_create_cart_for_customer(customer)
    try:
        pid = int(item.get('product_id') or key.split('_')[0])
    except Exception:
        return

    size = (item.get('size') or '')[:10]  # normalize
    qty = int(item.get('quantity') or 0)
    try:
        price = Decimal(str(item.get('price') or '0.00')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except Exception:
        price = Decimal('0.00')

    title = item.get('name') or ''
    image = item.get('image') or ''

    ci, created = CartItem.objects.get_or_create(
        cart=cart,
        product_id=pid,
        size=size,
        defaults={'quantity': qty, 'price': price, 'product_title': title, 'image_url': image}
    )
    if not created:
        ci.quantity = int(ci.quantity) + qty
        ci.price = price  # update price to latest server-side calculation
        if title:
            ci.product_title = title
        if image:
            ci.image_url = image
        ci.save()


def sync_session_cart_to_db(customer, session_cart):
    for key, item in session_cart.items():
        sync_session_item_to_db(customer, key, item)


def load_db_cart_into_session(request, customer):
    """
    Replace request.session['cart'] with the DB cart contents for this customer.
    """
    cart = get_or_create_cart_for_customer(customer)
    session_cart = {}
    for ci in cart.items.all():
        size = ci.size or ''
        if size:
            key = f"{ci.product_id}_{size}"
        else:
            key = f"{ci.product_id}"
        session_cart[key] = {
            'product_id': ci.product_id,
            'name': ci.product_title or '',
            'price': f"{ci.price:.2f}",
            'quantity': int(ci.quantity),
            'image': ci.image_url or '',
            'size': ci.size or ''
        }
    request.session['cart'] = session_cart
    request.session['cart_count'] = sum(int(i.get('quantity', 0)) for i in session_cart.values())
    request.session.modified = True


def clear_db_cart_for_customer(customer):
    """
    Deletes the customer's DB cart and all its items.
    Used after checkout to ensure no stale items are reloaded later.
    """
    try:
        cart = Cart.objects.filter(customer=customer).first()
        if cart:
            # delete all items linked to this cart
            CartItem.objects.filter(cart=cart).delete()
            # delete the cart itself
            cart.delete()
    except Exception:
        # silently ignore (you could log this in production)
        pass
