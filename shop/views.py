# shop/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.templatetags.static import static
from django.http import JsonResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST,require_http_methods
from django.contrib import messages
from django.contrib.messages import get_messages
from decimal import Decimal, ROUND_HALF_UP
from .forms import SignUpForm
from django.contrib.auth.hashers import check_password
from django.db import transaction
from .utils import sync_session_item_to_db, sync_session_cart_to_db, load_db_cart_into_session, get_or_create_cart_for_customer,clear_db_cart_for_customer
from .models import Product, Category, Customer_Table, Cart, CartItem, CustomerOrder, Cosmetic, Jewellery, Bag, Shoes, ContactMessage, CustomerOrder, Wishlist
import json
 
def sign_up(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created successfully Please Login here!")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = SignUpForm()
    return render(request, 'shop/sign_up.html', {'form': form})


def login_view(request):
    """
    Authenticate customer (simple DB-backed email + hashed password check).
    On successful login:
      - merge guest session cart into DB cart
      - reload DB cart into session (merged result)
      - set session customer info
    """
    if request.method == "POST":
        email = request.POST.get('customer[email]', '').strip()
        password = request.POST.get('customer[password]', '').strip()

        # basic validation
        if not email or not password:
            messages.error(request, "Please enter both email and password.")
            return render(request, 'shop/login.html')

        try:
            customer = Customer_Table.objects.get(email=email)
        except Customer_Table.DoesNotExist:
            messages.error(request, "Email not found. Please create an account.")
            return render(request, 'shop/login.html')

        # Password check (assumes stored password is hashed and check_password works)
        if not check_password(password, customer.password):
            messages.error(request, "Incorrect password.")
            return render(request, 'shop/login.html')

        # Merge guest session cart into DB cart if session has items
        session_cart = request.session.get('cart', {}) or {}
        if session_cart:
            try:
                # safe: sync will create cart & items as needed
                sync_session_cart_to_db(customer, session_cart)
            except Exception:
                # don't break login on sync failure; log in production
                pass

        # Load DB cart into session (this will override or merge keys from DB)
        try:
            load_db_cart_into_session(request, customer)
        except Exception:
            # unexpected error loading DB cart should not stop login
            pass

        # set login session keys
        request.session['customer_id'] = customer.customer_id
        request.session['customer_name'] = getattr(customer, 'first_name', '')
        # ensure cart_count exists (load_db_cart_into_session sets it already)
        request.session.setdefault('cart_count', sum(int(it.get('quantity', 0)) for it in request.session.get('cart', {}).values()))
        request.session.modified = True

        messages.success(request, f"Welcome back, {customer.first_name or 'Customer'}!")
        return redirect('index')

    # GET -> show login template
    return render(request, 'shop/login.html')


def logout_view(request):
    list(get_messages(request))
    request.session.flush()
    messages.success(request, "You have been logged out.")
    return redirect('login')


def index(request):
    categories = Category.objects.all()

    def get_products(slug, limit=None):
        """Fetch products by slug (fallback: all products) and enrich them."""
        try:
            category = Category.objects.get(slug=slug)
            qs = category.products.filter(available=True).order_by('-created')
        except Category.DoesNotExist:
            qs = Product.objects.filter(available=True).order_by('-created')

        if limit:
            qs = qs[:limit]

        # --- enrich each product ---
        placeholder = static('images/product-images/placeholder.jpg')
        placeholder_hover = static('images/product-images/placeholder_hover.jpg')

        products = list(qs)
        for p in products:
            p.image_url = p.image.url if getattr(p, 'image', None) and hasattr(p.image, 'url') else placeholder
            p.hover_url = (
                p.hover_image.url
                if getattr(p, 'hover_image', None) and hasattr(p.hover_image, 'url')
                else (p.image.url if getattr(p, 'image', None) and hasattr(p.image, 'url') else placeholder_hover)
            )
            p.sizes_list = getattr(p, 'sizes', []) or []
            p.colors_list = getattr(p, 'colors', []) or []
        return products

    womens_products = get_products('women_dresses', limit=6)
    mens_products = get_products('mens_wear', limit=6)
    women_featured_collection = get_products('women_featured_collection', limit=6)  # Added featured products
    men_featured_collection = get_products('men_featured_collection', limit=6)  # Added featured products


    return render(request, 'shop/index.html', {
        'categories': categories,
        'womens_products': womens_products,
        'mens_products': mens_products,
        'women_featured_products': women_featured_collection, 
        'men_featured_products':men_featured_collection, # Pass to template
    })


def product_info(request, pk):
    """
    Product detail page by numeric product_id (pk).
    Adds sizes_with_prices: [{'size':'S','price': Decimal('xx.xx')}, ...]
    """
    product = get_object_or_404(Product, product_id=pk)

    # --- Local constants for this function only ---
    SIZE_PRICE_OFFSETS = {
        'S': Decimal('0'),
        'M': Decimal('5'),
        'L': Decimal('10'),
        'XL': Decimal('15'),
        'XXL': Decimal('20'),
    }
    SIZE_ORDER = ['S', 'M', 'L', 'XL', 'XXL']
    # ---------------------------------------------

    # placeholders
    placeholder = static('images/product-detail-page/product-placeholder.jpg')
    placeholder_hover = static('images/product-detail-page/product-placeholder-hover.jpg')

    # primary image
    image_url = product.image.url if getattr(product, 'image', None) and hasattr(product.image, 'url') else placeholder
    # hover image fallback
    hover_url = (
        product.hover_image.url
        if getattr(product, 'hover_image', None) and hasattr(product.hover_image, 'url')
        else (product.image.url if getattr(product, 'image', None) and hasattr(product.image, 'url') else placeholder_hover)
    )

    # gallery
    gallery_images = []
    if getattr(product, 'image', None) and hasattr(product.image, 'url'):
        gallery_images.append(product.image.url)
    if getattr(product, 'hover_image', None) and hasattr(product.hover_image, 'url'):
        if product.hover_image.url not in gallery_images:
            gallery_images.append(product.hover_image.url)
    if not gallery_images:
        gallery_images = [placeholder, placeholder_hover]

    # base price
    try:
        base_price = Decimal(str(product.price))
    except Exception:
        base_price = Decimal('0.00')

    # sizes with prices
    sizes_with_prices = []
    for size in SIZE_ORDER:
        offset = SIZE_PRICE_OFFSETS.get(size, Decimal('0'))
        price = (base_price + offset).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        sizes_with_prices.append({
            'size': size,
            'price': price,
            'price_str': f"{price:.2f}"
        })

    context = {
        'product': product,
        'image_url': image_url,
        'hover_url': hover_url,
        'gallery_images': gallery_images,
        'sizes_with_prices': sizes_with_prices,
        'default_size': sizes_with_prices[0]['size'] if sizes_with_prices else None,
    }
    return render(request, 'shop/product_info.html', context)


def add_to_cart(request, category, item_id):
    """
    Generic add-to-cart for multiple categories.
    Keeps original product size logic for 'product' (clothes) and 'shoe'.
    For other categories (cosmetic, jewelry, bag) size is not used.
    Stores in session.cart with keys:
      - products/shoes with size: "<item_id>_<SIZE>"  (same as original)
      - others: "<category>_<item_id>"
    """
    # local constants for price offsets (unchanged)
    SIZE_PRICE_OFFSETS = {
        'S': Decimal('0'),
        'M': Decimal('5'),
        'L': Decimal('10'),
        'XL': Decimal('15'),
        'XXL': Decimal('20'),
    }
    SIZE_ORDER = ['S', 'M', 'L', 'XL', 'XXL']

    # find the object depending on category
    obj = None
    if category == 'product':
        obj = get_object_or_404(Product, product_id=item_id)
    elif category == 'cosmetic':
        obj = get_object_or_404(Cosmetic, cosmetic_product_id=item_id)
    elif category == 'jewellery':
        obj = get_object_or_404(Jewellery, jewellery_product_id=item_id)
    elif category == 'shoes':
        obj = get_object_or_404(Shoes, shoes_product_id=item_id)
    elif category == 'bag':
        obj = get_object_or_404(Bag, bag_product_id=item_id)
    else:
        # unknown category: redirect safely
        return redirect('index')

    # image fallback
    if getattr(obj, 'image', None) and hasattr(obj.image, 'url'):
        image_url = obj.image.url
    else:
        image_url = static('images/product-images/default-product.jpg')

    # decide whether to use size: only for 'product' (clothes) and 'shoe'
    selected_size = None
    if category in ('product', 'shoe'):
        selected_size = (request.POST.get('size') or request.GET.get('size') or None)
        if not selected_size:
            available_sizes = list(getattr(obj, 'sizes', []) or [])
            selected_size = available_sizes[0] if available_sizes else SIZE_ORDER[0]
        selected_size = selected_size.upper()

    # compute base price
    try:
        base_price = Decimal(str(getattr(obj, 'price', 0)))
    except Exception:
        base_price = Decimal('0.00')

    if selected_size:
        offset = SIZE_PRICE_OFFSETS.get(selected_size, Decimal('0'))
        final_price = (base_price + offset).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    else:
        final_price = base_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    final_price_str = f"{final_price:.2f}"

    # build cart key: keep legacy product style "<id>_<SIZE>" when size present,
    # otherwise use "<category>_<id>"
    if selected_size:
        cart_key = f"{item_id}_{selected_size}"
    else:
        cart_key = f"{category}_{item_id}"

    cart = request.session.get('cart', {})

    if cart_key in cart:
        cart[cart_key]['quantity'] = int(cart[cart_key].get('quantity', 0)) + 1
        cart[cart_key].setdefault('name', getattr(obj, 'title', getattr(obj, 'name', 'Item')))
        cart[cart_key].setdefault('image', image_url)
        cart[cart_key]['price'] = final_price_str
        if selected_size:
            cart[cart_key]['size'] = selected_size
    else:
        cart[cart_key] = {
            # keep old product_id field when applicable, else include category/item id
            'product_id': getattr(obj, 'product_id', getattr(obj, 'cosmetic_product_id', None)),
            'name': getattr(obj, 'title', getattr(obj, 'name', 'Item')),
            'price': final_price_str,
            'quantity': 1,
            'image': image_url,
        }
        if selected_size:
            cart[cart_key]['size'] = selected_size

    request.session['cart'] = cart
    request.session['cart_count'] = sum(int(item.get('quantity', 0)) for item in cart.values())
    request.session.modified = True

    # Optional DB sync for logged-in customers (keeps your existing behavior)
    cust_id = request.session.get('customer_id')
    if cust_id:
        try:
            customer = Customer_Table.objects.get(customer_id=cust_id)
        except Customer_Table.DoesNotExist:
            customer = None
        if customer:
            try:
                sync_session_item_to_db(customer, cart_key, cart[cart_key])
            except Exception:
                # ignore sync errors to avoid breaking UX
                pass

    return redirect('cart_detail')


def cart_detail(request):
    """
    Cart detail supporting:
     - legacy product keys "<product_id>_<SIZE>" (size-aware)
     - new category keys "<category>_<item_id>" for cosmetic/jewelry/bag (no size)
     - shoe can be provided as legacy style with size or as 'shoe_<id>' (no size)
    Displays: name, image, quantity, price, size (or '-' when not applicable).
    """
    # attempt to load DB cart into session for logged-in user (existing behavior)
    cust_id = request.session.get('customer_id')
    if cust_id:
        session_cart = request.session.get('cart', {})
        if not session_cart:
            try:
                customer = Customer_Table.objects.get(customer_id=cust_id)
                load_db_cart_into_session(request, customer)
            except Customer_Table.DoesNotExist:
                pass

    cart = request.session.get('cart', {})  # session cart
    updated = False

    # local constants for price offsets (used when size applies)
    SIZE_PRICE_OFFSETS = {
        'S': Decimal('0'),
        'M': Decimal('5'),
        'L': Decimal('10'),
        'XL': Decimal('15'),
        'XXL': Decimal('20'),
    }

    placeholder = static('images/product-images/default-product.jpg')
    display_cart = {}

    for key, item in list(cart.items()):
        quantity = int(item.get('quantity', 0))
        name = item.get('name')
        image = item.get('image')
        price_str = item.get('price')  # stored as string
        size = item.get('size') if item.get('size') else None

        # Decide key format:
        # 1) Legacy product/shoe with size: "<id>_<SIZE>" where first part is numeric -> consider as product_id
        # 2) New category keys: "<category>_<id>" -> category is non-numeric (e.g., 'cosmetic', 'bag', 'jewelry', 'shoe')
        category = None
        item_id = None
        is_legacy_product_key = False

        if isinstance(key, str) and '_' in key:
            first_part, rest = key.split('_', 1)
            # if first_part is numeric -> legacy "<id>_<SIZE>"
            if first_part.isdigit():
                is_legacy_product_key = True
                item_id = int(first_part)
                # if rest looks like size keep it; else keep item['size'] if present
                if not size:
                    size = rest.upper()
            else:
                # new format: "<category>_<item_id>"
                category = first_part
                try:
                    item_id = int(rest)
                except ValueError:
                    item_id = None
        else:
            # key without underscore: try parse as numeric id (legacy) otherwise skip
            try:
                item_id = int(key)
                is_legacy_product_key = True
            except Exception:
                # unknown key format — skip or fill defaults
                item_id = None

        # attempt to fetch DB object based on category / legacy key
        product_obj = None
        if is_legacy_product_key:
            # legacy numeric keys represent products
            try:
                product_obj = Product.objects.get(product_id=item_id)
                category = 'product'
            except Product.DoesNotExist:
                product_obj = None
        else:
            # category-based lookup
            if category == 'cosmetic':
                try:
                    product_obj = Cosmetic.objects.get(cosmetic_product_id=item_id)
                except Cosmetic.DoesNotExist:
                    product_obj = None
            elif category == 'jewellery':
                try:
                    product_obj = Jewellery.objects.get(jewellery_product_id=item_id)
                except Jewellery.DoesNotExist:
                    product_obj = None
            elif category == 'shoes':
                try:
                    product_obj = Shoes.objects.get(shoes_product_id=item_id)
                
                except Shoes.DoesNotExist:
                    product_obj = None
                    
            elif category == 'bag':
                try:
                    product_obj = Bag.objects.get(bag_product_id=item_id)
                except Bag.DoesNotExist:
                    product_obj = None
            else:
                product_obj = None

        # Fill missing name/image/price from DB when available
        if product_obj:
            # name
            if not name:
                # use title or name (models differ)
                name = getattr(product_obj, 'title', getattr(product_obj, 'name', 'Unknown product'))
                cart[key]['name'] = name
                updated = True

            # image
            if not image or not isinstance(image, str) or not image.strip():
                image_field = getattr(product_obj, 'image', None)
                if getattr(image_field, 'url', None):
                    image = image_field.url
                else:
                    image = placeholder
                cart[key]['image'] = image
                updated = True

            # price: if size applies, recalculate using offsets
            if size:
                try:
                    base_price = Decimal(str(getattr(product_obj, 'price', '0.00')))
                except Exception:
                    base_price = Decimal('0.00')
                offset = SIZE_PRICE_OFFSETS.get(size.upper(), Decimal('0'))
                recalculated = (base_price + offset).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                recalculated_str = f"{recalculated:.2f}"
                if price_str != recalculated_str:
                    price_str = recalculated_str
                    cart[key]['price'] = price_str
                    cart[key]['size'] = size.upper()
                    updated = True
            else:
                # no size — ensure price present (use DB price)
                if not price_str:
                    price_str = f"{Decimal(str(getattr(product_obj, 'price', '0.00'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
                    cart[key]['price'] = price_str
                    updated = True
        else:
            # DB object not found — ensure defaults
            name = name or "Unknown product"
            price_str = price_str or "0.00"
            image = image or placeholder
            if cart.get(key) is None:
                cart[key] = {}
            cart[key].setdefault('name', name)
            cart[key].setdefault('price', price_str)
            cart[key].setdefault('image', image)
            updated = True

        # ensure quantity non-negative
        if quantity < 0:
            quantity = 0
            cart[key]['quantity'] = 0
            updated = True

        # For display: size should be shown for products & shoes, otherwise '-'
        display_size = size.upper() if size and (category in ('product', 'shoe') or is_legacy_product_key) else '-'

        display_cart[key] = {
            'category': category if category else ('product' if is_legacy_product_key else None),
            'item_id': item_id,
            'name': name,
            'image': image,
            'price': price_str,
            'quantity': quantity,
            'size': display_size,
        }

    # persist any session fixes
    if updated:
        request.session['cart'] = cart
        request.session.modified = True

    # calculate total
    total = Decimal('0.00')
    for it in display_cart.values():
        try:
            total += Decimal(str(it['price'])) * int(it['quantity'])
        except Exception:
            continue
    try:
        total_price = float(total)
    except Exception:
        total_price = 0.0

    # update cart_count
    request.session['cart_count'] = sum(int(it.get('quantity', 0)) for it in cart.values())

    return render(request, 'shop/cart.html', {'cart': display_cart, 'total_price': total_price})


@require_POST
def update_cart(request):
    """
    Update session cart (same behavior as before) AND update DB CartItem rows
    when a customer is logged in (request.session['customer_id']).
    """
    cart = request.session.get('cart', {})

    def to_int(v, default=0):
        try:
            return int(v)
        except Exception:
            return default

    # Helper to parse a session cart key into (product_id:int, size:str|None)
    def parse_cart_key(key):
        if isinstance(key, str) and '_' in key:
            pid_part, size_part = key.split('_', 1)
            try:
                pid = int(pid_part)
            except Exception:
                pid = None
            size = size_part or ''
        else:
            try:
                pid = int(key)
            except Exception:
                pid = None
            size = ''
        return pid, (size.upper() if size else '')

    # Find logged-in customer (if any)
    customer = None
    cust_id = request.session.get('customer_id')
    if cust_id:
        try:
            customer = Customer_Table.objects.get(customer_id=cust_id)
        except Customer_Table.DoesNotExist:
            customer = None

    # If AJAX JSON request
    if request.content_type == 'application/json':
        import json
        try:
            payload = json.loads(request.body.decode('utf-8') or '{}')
        except Exception:
            return HttpResponseBadRequest("Invalid JSON")

        changed = False

        # We will track DB changes to apply in a transaction if customer exists
        db_changes = []

        for raw_pid, instr in payload.items():
            pid_key = str(raw_pid)
            if pid_key not in cart:
                # skip missing items
                continue

            cur_qty = to_int(cart[pid_key].get('quantity', 0), 0)

            if isinstance(instr, dict) and 'op' in instr:
                op = instr.get('op')
                if op == 'inc':
                    new_qty = cur_qty + 1
                elif op == 'dec':
                    new_qty = max(0, cur_qty - 1)
                else:
                    continue
            else:
                new_qty = to_int(instr, cur_qty)

            # apply change to session cart
            if new_qty <= 0:
                # remove from session
                del cart[pid_key]
                changed = True
                # prepare DB removal
                if customer:
                    db_changes.append(('remove', pid_key))
            else:
                if cart[pid_key].get('quantity') != new_qty:
                    cart[pid_key]['quantity'] = new_qty
                    changed = True
                    # prepare DB set
                    if customer:
                        db_changes.append(('set', pid_key, new_qty))

        if changed:
            request.session['cart'] = cart
            request.session['cart_count'] = sum(int(i.get('quantity', 0)) for i in cart.values())
            request.session.modified = True

        # Apply DB changes in a single transaction
        if customer and db_changes:
            with transaction.atomic():
                db_cart = get_or_create_cart_for_customer(customer)
                for change in db_changes:
                    if change[0] == 'remove':
                        key = change[1]
                        pid, size = parse_cart_key(key)
                        if pid is None:
                            continue
                        # remove cartitem if exists
                        CartItem.objects.filter(cart=db_cart, product_id=pid, size=(size or '')).delete()
                    elif change[0] == 'set':
                        _, key, qty = change
                        pid, size = parse_cart_key(key)
                        if pid is None:
                            continue
                        # update or create the DB CartItem (set exact qty)
                        try:
                            ci = CartItem.objects.get(cart=db_cart, product_id=pid, size=(size or ''))
                            if qty <= 0:
                                ci.delete()
                            else:
                                ci.quantity = qty
                                ci.save()
                        except CartItem.DoesNotExist:
                            if qty > 0:
                                # create with price from session item if present
                                sess_item = cart.get(key)
                                price = sess_item and sess_item.get('price') or '0.00'
                                from decimal import Decimal
                                try:
                                    price_dec = Decimal(str(price))
                                except Exception:
                                    price_dec = Decimal('0.00')
                                CartItem.objects.create(
                                    cart=db_cart,
                                    product_id=pid,
                                    size=(size or ''),
                                    quantity=qty,
                                    price=price_dec,
                                    product_title=sess_item.get('name') if sess_item else '',
                                    image_url=sess_item.get('image') if sess_item else '',
                                )

        # compute totals for response
        total_price = 0.0
        for item in cart.values():
            try:
                total_price += float(item.get('price', 0)) * int(item.get('quantity', 0))
            except Exception:
                continue

        return JsonResponse({
            'cart_count': request.session.get('cart_count', 0),
            'total_price': f"{total_price:.2f}",
        })

    # Non-AJAX (regular form submit)
    changed = False
    db_changes = []
    for pid_str, item in list(cart.items()):
        form_name = f"quantity-{pid_str}"
        raw = request.POST.get(form_name)
        if raw is None:
            continue
        qty = to_int(raw, to_int(item.get('quantity', 0)))
        if qty <= 0:
            del cart[pid_str]
            changed = True
            if customer:
                db_changes.append(('remove', pid_str))
        else:
            if item.get('quantity') != qty:
                cart[pid_str]['quantity'] = qty
                changed = True
                if customer:
                    db_changes.append(('set', pid_str, qty))

    if changed:
        request.session['cart'] = cart
        request.session['cart_count'] = sum(int(i.get('quantity', 0)) for i in cart.values())
        request.session.modified = True

    if customer and db_changes:
        with transaction.atomic():
            db_cart = get_or_create_cart_for_customer(customer)
            for change in db_changes:
                if change[0] == 'remove':
                    _, key = change
                    pid, size = parse_cart_key(key)
                    if pid is None:
                        continue
                    CartItem.objects.filter(cart=db_cart, product_id=pid, size=(size or '')).delete()
                elif change[0] == 'set':
                    _, key, qty = change
                    pid, size = parse_cart_key(key)
                    if pid is None:
                        continue
                    try:
                        ci = CartItem.objects.get(cart=db_cart, product_id=pid, size=(size or ''))
                        if qty <= 0:
                            ci.delete()
                        else:
                            ci.quantity = qty
                            ci.save()
                    except CartItem.DoesNotExist:
                        if qty > 0:
                            sess_item = cart.get(key)
                            price = sess_item and sess_item.get('price') or '0.00'
                            from decimal import Decimal
                            try:
                                price_dec = Decimal(str(price))
                            except Exception:
                                price_dec = Decimal('0.00')
                            CartItem.objects.create(
                                cart=db_cart,
                                product_id=pid,
                                size=(size or ''),
                                quantity=qty,
                                price=price_dec,
                                product_title=sess_item.get('name') if sess_item else '',
                                image_url=sess_item.get('image') if sess_item else '',
                            )

    return redirect('cart_detail')


@require_http_methods(["GET", "POST"])
def remove_from_cart(request, key):
    """
    Remove session cart item by exact key (e.g. '5_M'). Also remove corresponding DB CartItem if user logged in.
    """
    cart = request.session.get('cart', {})
    removed = False

    if key in cart:
        del cart[key]
        removed = True
        request.session['cart'] = cart
        request.session['cart_count'] = sum(int(i.get('quantity', 0)) for i in cart.values())
        request.session.modified = True

    # If logged-in, remove DB CartItem
    cust_id = request.session.get('customer_id')
    if cust_id:
        try:
            customer = Customer_Table.objects.get(customer_id=cust_id)
        except Customer_Table.DoesNotExist:
            customer = None
        if customer:
            # parse key
            if isinstance(key, str) and '_' in key:
                pid_part, size_part = key.split('_', 1)
                try:
                    pid = int(pid_part)
                except Exception:
                    pid = None
                size = (size_part or '')
            else:
                try:
                    pid = int(key)
                except Exception:
                    pid = None
                size = ''
            if pid is not None:
                try:
                    cart_obj = Cart.objects.get(customer=customer)
                except Cart.DoesNotExist:
                    cart_obj = None
                if cart_obj:
                    CartItem.objects.filter(cart=cart_obj, product_id=pid, size=(size or '')).delete()

    # AJAX or JSON request -> return JSON summary
    if request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.content_type == 'application/json':
        total_price = 0.0
        for item in cart.values():
            try:
                total_price += float(item['price']) * int(item['quantity'])
            except Exception:
                continue
        return JsonResponse({
            'removed': removed,
            'cart_count': request.session.get('cart_count', 0),
            'total_price': f"{total_price:.2f}",
        })

    return redirect('cart_detail')


def checkout(request):
    """
    Show checkout page / process order.
    - Uses session cart to display items and build order
    - On POST: creates CustomerOrder, clears DB cart and session cart
    """
    cart = request.session.get('cart', {}) or {}
    if not cart:
        messages.warning(request, "Your cart is empty!")
        return redirect('index')

    # Prepare display and database-friendly representation
    display_cart_for_template = {}
    display_cart_for_db = []
    total_price = Decimal('0.00')

    # iterate session cart
    for pid_key, item in cart.items():
        try:
            quantity = int(item.get('quantity', 0))
        except Exception:
            quantity = 0
        try:
            unit_price = Decimal(str(item.get('price', '0.00'))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        except Exception:
            unit_price = Decimal('0.00')

        subtotal = unit_price * max(quantity, 0)
        total_price += subtotal

        size = item.get('size', '') or ''
        name = item.get('name') or item.get('product_title') or 'Unknown item'

        # For template
        display_cart_for_template[pid_key] = {
            'name': name,
            'price': float(unit_price),
            'quantity': quantity,
            'size': size,
            'subtotal': float(subtotal),
        }

        # For DB storage in order (simple serializable dict)
        display_cart_for_db.append({
            'product_name': name,
            'price': float(unit_price),
            'quantity': quantity,
            'size': size,
            'subtotal': float(subtotal),
            'session_key': pid_key,
        })

    shipping = Decimal('50.00')
    total_with_shipping = (total_price + shipping).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    if request.method == "POST":
        # require customer logged in (cust_id is numeric stored in session)
        cust_id = request.session.get('customer_id')
        if not cust_id:
            messages.error(request, "You must be logged in to place an order. Please login or create an account.")
            return redirect('login')

        # collect billing/shipping fields from POST
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        telephone = request.POST.get('telephone', '').strip()
        company = request.POST.get('company', '').strip()
        address = request.POST.get('address', '').strip()
        apartment = request.POST.get('apartment', '').strip()
        city = request.POST.get('city', '').strip()
        postcode = request.POST.get('postcode', '').strip()
        country = request.POST.get('country', '').strip()
        region_state = request.POST.get('region_state', '').strip()
        payment_method = request.POST.get('payment_method', 'Not specified').strip()
        order_notes = request.POST.get('order_notes', '').strip()

        # Minimal validation
        if not first_name or not last_name or not address or not city:
            messages.error(request, "Please fill required address and name fields.")
            return render(request, 'shop/checkout.html', {
                'cart': display_cart_for_template,
                'total_price': float(total_price),
                'shipping': float(shipping),
                'total_with_shipping': float(total_with_shipping),
            })

        # Save order inside a transaction (so clearing cart happens after successful creation)
        try:
            with transaction.atomic():
                # fetch customer instance
                customer = Customer_Table.objects.get(customer_id=cust_id)

                # create CustomerOrder (assumes order_items is JSONField or similar)
                order = CustomerOrder.objects.create(
                    customer_id=cust_id,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    telephone=telephone,
                    company=company,
                    address=address,
                    apartment=apartment,
                    city=city,
                    postcode=postcode,
                    country=country,
                    region_state=region_state,
                    payment_method=payment_method,
                    order_notes=order_notes,
                    order_items=display_cart_for_db,
                    total_price=float(total_with_shipping),
                )

                # Clear DB cart for this customer so it's not reloaded on future login
                try:
                    clear_db_cart_for_customer(customer)
                except Exception:
                    # swallow errors clearing DB cart but ensure order persists
                    pass

                # Clear session cart and update counters
                request.session['cart'] = {}
                request.session['cart_count'] = 0
                request.session.modified = True

        except Customer_Table.DoesNotExist:
            messages.error(request, "Customer record not found. Please login again.")
            return redirect('login')
        except Exception as exc:
            # Unexpected error while creating order
            messages.error(request, "There was an error processing your order. Please try again.")
            # optionally log exc in production
            return render(request, 'shop/checkout.html', {
                'cart': display_cart_for_template,
                'total_price': float(total_price),
                'shipping': float(shipping),
                'total_with_shipping': float(total_with_shipping),
            })

        messages.success(request, "Your order has been placed successfully!")
        return redirect('index')

    # GET -> render checkout form with cart contents
    # ensure cart_count is accurate for templates
    request.session['cart_count'] = sum(int(it.get('quantity', 0)) for it in cart.values())
    request.session.modified = True

    return render(request, 'shop/checkout.html', {
        'cart': display_cart_for_template,
        'total_price': float(total_price),
        'shipping': float(shipping),
        'total_with_shipping': float(total_with_shipping),
    })


def women_shop(request):
    # --- Base queryset: all women products available ---
    base_qs = Product.objects.filter(category__name__istartswith='women', available=True)

    # --- Read filters from GET ---
    selected_collections = request.GET.getlist('collection')
    selected_brands = request.GET.getlist('brand')
    selected_sizes = request.GET.getlist('size')
    selected_colors = request.GET.getlist('color')
    selected_price_ranges = request.GET.getlist('price')

    # --- Apply DB-level filters (brand + price) ---
    if selected_brands:
        base_qs = base_qs.filter(brand__in=selected_brands)

    if selected_price_ranges:
        price_qs = base_qs.none()
        for pr in selected_price_ranges:
            try:
                low, high = map(float, pr.split('-'))
            except:
                continue
            price_qs |= base_qs.filter(price__gte=low, price__lte=high)
        base_qs = price_qs

    # --- Prepare products list with Python-side filters for collections, sizes, colors ---
    products = []
    placeholder = static('images/product-images/placeholder.jpg')
    placeholder_hover = static('images/product-images/placeholder_hover.jpg')

    for p in base_qs.order_by('-created'):
        # Collection filter
        if selected_collections and not any(sc in (p.collection_cat or []) for sc in selected_collections):
            continue
        # Size filter
        if selected_sizes and not any(sz in (p.sizes or []) for sz in selected_sizes):
            continue
        # Color filter
        if selected_colors and not any(cl in (p.colors or []) for cl in selected_colors):
            continue

        # Enrich product object for template
        p.image_url = getattr(p.image, 'url', placeholder)
        p.hover_url = getattr(p.hover_image, 'url', getattr(p.image, 'url', placeholder_hover))
        p.sizes_list = list(p.sizes or [])
        p.colors_list = list(p.colors or [])
        products.append(p)

    # --- Build filter options (all available values) ---
    women_products = Product.objects.filter(category__name__istartswith='women')

    # Collections (first-seen order)
    collections = []
    for p in women_products:
        for c in (p.collection_cat or []):
            if c not in collections:
                collections.append(c)

    # Sizes (first-seen order)
    sizes = []
    for p in women_products:
        for s in (p.sizes or []):
            if s not in sizes:
                sizes.append(s)

    # Colors (use COLOR_CHOICES order, only existing in DB)
    color_master_list = [c[0] for c in Product.COLOR_CHOICES]
    colors_in_db = set()
    for p in women_products:
        colors_in_db.update(p.colors or [])
    colors = [c for c in color_master_list if c in colors_in_db]

    # Brands
    brands = [b for b in women_products.values_list('brand', flat=True).distinct() if b]

    # Price ranges (display vs filter)
    price_ranges = []
    step = 50
    for i in range(0, 500, step):
        if i == 0:
            price_ranges.append((f"{i}-{i+step}", f"${i} - ${i+step}"))
        else:
            price_ranges.append((f"{i+1}-{i+step}", f"${i} - ${i+step}"))

    # --- Prepare context for template ---
    context = {
        'products': products,
        'brands': brands,
        'selected_brands': selected_brands,
        'collections': collections,
        'selected_collections': selected_collections,
        'sizes': sizes,
        'selected_sizes': selected_sizes,
        'colors': colors,
        'selected_colors': selected_colors,
        'price_ranges': price_ranges,
        'selected_price_ranges': selected_price_ranges,
        'partial': False
    }

    return render(request, 'shop/women_shop.html', context)


def men_shop(request):
    # --- Base queryset: all men products available ---
    base_qs = Product.objects.filter(category__name__istartswith='men', available=True)

    # --- Read filters from GET ---
    selected_collections = request.GET.getlist('collection')
    selected_brands = request.GET.getlist('brand')
    selected_sizes = request.GET.getlist('size')
    selected_colors = request.GET.getlist('color')
    selected_price_ranges = request.GET.getlist('price')

    # --- Apply DB-level filters (brand + price) ---
    if selected_brands:
        base_qs = base_qs.filter(brand__in=selected_brands)

    if selected_price_ranges:
        price_qs = base_qs.none()
        for pr in selected_price_ranges:
            try:
                low, high = map(float, pr.split('-'))
            except:
                continue
            price_qs |= base_qs.filter(price__gte=low, price__lte=high)
        base_qs = price_qs

    # --- Prepare products list with Python-side filters for collections, sizes, colors ---
    products = []
    placeholder = static('images/product-images/placeholder.jpg')
    placeholder_hover = static('images/product-images/placeholder_hover.jpg')

    for p in base_qs.order_by('-created'):
        # Collection filter
        if selected_collections and not any(sc in (p.collection_cat or []) for sc in selected_collections):
            continue
        # Size filter
        if selected_sizes and not any(sz in (p.sizes or []) for sz in selected_sizes):
            continue
        # Color filter
        if selected_colors and not any(cl in (p.colors or []) for cl in selected_colors):
            continue

        # Enrich product object for template
        p.image_url = getattr(p.image, 'url', placeholder)
        p.hover_url = getattr(p.hover_image, 'url', getattr(p.image, 'url', placeholder_hover))
        p.sizes_list = list(p.sizes or [])
        p.colors_list = list(p.colors or [])
        products.append(p)

    # --- Build filter options (all available values) ---
    men_products = Product.objects.filter(category__name__istartswith='men')

    # Collections (first-seen order)
    collections = []
    for p in men_products:
        for c in (p.collection_cat or []):
            if c not in collections:
                collections.append(c)

    # Sizes (first-seen order)
    sizes = []
    for p in men_products:
        for s in (p.sizes or []):
            if s not in sizes:
                sizes.append(s)

    # Colors (use COLOR_CHOICES order, only existing in DB)
    color_master_list = [c[0] for c in Product.COLOR_CHOICES]
    colors_in_db = set()
    for p in men_products:
        colors_in_db.update(p.colors or [])
    colors = [c for c in color_master_list if c in colors_in_db]

    # Brands
    brands = [b for b in men_products.values_list('brand', flat=True).distinct() if b]

    # Price ranges (display vs filter)
    price_ranges = []
    step = 50
    for i in range(0, 500, step):
        if i == 0:
            price_ranges.append((f"{i}-{i+step}", f"${i} - ${i+step}"))
        else:
            price_ranges.append((f"{i+1}-{i+step}", f"${i} - ${i+step}"))

    # --- Prepare context for template ---
    context = {
        'products': products,
        'brands': brands,
        'selected_brands': selected_brands,
        'collections': collections,
        'selected_collections': selected_collections,
        'sizes': sizes,
        'selected_sizes': selected_sizes,
        'colors': colors,
        'selected_colors': selected_colors,
        'price_ranges': price_ranges,
        'selected_price_ranges': selected_price_ranges,
        'partial': False
    }

    return render(request, 'shop/men_shop.html', context)


def cosmetic(request):
    """
    Build three collection lists for the cosmetics slider:
      - We_recommed
      - Whats_new
      - Best_offer

    Each cosmetic is enriched with:
      - image_url, hover_url, gallery list
      - price_str
      - detail_url (reverse name: 'cosmetic_info' expects pk)
    """
    # placehoders
    placeholder = static('images/product-detail-page/product-placeholder.jpg')
    placeholder_hover = static('images/product-detail-page/product-placeholder-hover.jpg')

    # fetch all cosmetics once
    all_cosmetics = Cosmetic.objects.all()

    # helper to get image urls safely
    def get_image_urls(obj):
        img = obj.image.url if getattr(obj, 'image', None) and hasattr(obj.image, 'url') else placeholder
        hover = obj.image_hover.url if getattr(obj, 'image_hover', None) and hasattr(obj.image_hover, 'url') else (img or placeholder_hover)
        gallery = []
        if getattr(obj, 'image', None) and hasattr(obj.image, 'url'):
            gallery.append(obj.image.url)
        if getattr(obj, 'image_hover', None) and hasattr(obj.image_hover, 'url') and obj.image_hover.url not in gallery:
            gallery.append(obj.image_hover.url)
        if not gallery:
            gallery = [placeholder, placeholder_hover]
        return img, hover, gallery

    # collections keys (as stored in MultiSelectField)
    RECOMMEND_KEY = 'We_recommed'
    WHATSNEW_KEY  = 'Whats_new'
    BESTOFFER_KEY = 'Best_offer'

    # helper to build enriched list for a given key
    def build_list_for_key(key):
        out = []
        for c in all_cosmetics:
            if c.collection and key in (c.collection or []):
                img, hover, gallery = get_image_urls(c)
                try:
                    price = Decimal(str(c.price))
                except Exception:
                    price = Decimal('0.00')
                price_str = f"{price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
                out.append({
                    'obj': c,
                    'image_url': img,
                    'hover_url': hover,
                    'gallery': gallery,
                    'price': price,
                    'price_str': price_str,
                    'detail_url': f"{c.get_absolute_url()}" if hasattr(c, 'get_absolute_url') else f"/cosmetics/{c.cosmetic_product_id}/",
                })
        return out

    context = {
        'we_recommed': build_list_for_key(RECOMMEND_KEY),
        'whats_new' : build_list_for_key(WHATSNEW_KEY),
        'best_offer' : build_list_for_key(BESTOFFER_KEY),
    }

    return render(request, 'shop/cosmetic.html', context)


def cosmetic_info(request, cosmetic_product_id):
    """
    Cosmetic product detail page by numeric cosmetic_product_id.
    """
    cosmetic = get_object_or_404(Cosmetic, cosmetic_product_id=cosmetic_product_id)

    # placeholders
    placeholder = static('images/product-detail-page/product-placeholder.jpg')
    placeholder_hover = static('images/product-detail-page/product-placeholder-hover.jpg')

    # primary image
    image_url = cosmetic.image.url if getattr(cosmetic, 'image', None) and hasattr(cosmetic.image, 'url') else placeholder
    # hover image fallback
    hover_url = (
        cosmetic.image_hover.url
        if getattr(cosmetic, 'image_hover', None) and hasattr(cosmetic.image_hover, 'url')
        else image_url
    )

    # gallery
    gallery_images = []
    if getattr(cosmetic, 'image', None) and hasattr(cosmetic.image, 'url'):
        gallery_images.append(cosmetic.image.url)
    if getattr(cosmetic, 'image_hover', None) and hasattr(cosmetic.image_hover, 'url'):
        if cosmetic.image_hover.url not in gallery_images:
            gallery_images.append(cosmetic.image_hover.url)
    if not gallery_images:
        gallery_images = [placeholder, placeholder_hover]

    # base price
    try:
        base_price = Decimal(str(cosmetic.price))
    except Exception:
        base_price = Decimal('0.00')

    context = {
        'cosmetic': cosmetic,
        'image_url': image_url,
        'hover_url': hover_url,
        'gallery_images': gallery_images,
        'price': base_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'brand': cosmetic.brand,
        'collection': cosmetic.collection,
        'short_desc': cosmetic.short_desc,
    }

    return render(request, 'shop/cosmetic_info.html', context)


def jewellery(request):
    """
    Build three collection lists for the jewellery slider:
      - Most_selling
      - Trending
      - Sale

    Each jewellery item is enriched with:
      - image_url, hover_url, gallery list
      - price_str
      - detail_url (reverse name: 'jewellery_info' expects pk)
    """
    # placeholders
    placeholder = static('images/product-detail-page/product-placeholder.jpg')
    placeholder_hover = static('images/product-detail-page/product-placeholder-hover.jpg')

    # fetch all jewellery items once
    all_jewellery = Jewellery.objects.all()

    # helper to get image urls safely
    def get_image_urls(obj):
        img = obj.image.url if getattr(obj, 'image', None) and hasattr(obj.image, 'url') else placeholder
        hover = obj.image_hover.url if getattr(obj, 'image_hover', None) and hasattr(obj.image_hover, 'url') else (img or placeholder_hover)
        gallery = []
        if getattr(obj, 'image', None) and hasattr(obj.image, 'url'):
            gallery.append(obj.image.url)
        if getattr(obj, 'image_hover', None) and hasattr(obj.image_hover, 'url') and obj.image_hover.url not in gallery:
            gallery.append(obj.image_hover.url)
        if not gallery:
            gallery = [placeholder, placeholder_hover]
        return img, hover, gallery

    # collections keys (as stored in MultiSelectField)
    MOST_SELLING_KEY = 'Most_selling'
    TRENDING_KEY     = 'Trending'
    SALE_KEY         = 'Sale'

    # helper to build enriched list for a given key
    def build_list_for_key(key):
        out = []
        for j in all_jewellery:
            if j.collection and key in (j.collection or []):
                img, hover, gallery = get_image_urls(j)
                try:
                    price = Decimal(str(j.price))
                except Exception:
                    price = Decimal('0.00')
                price_str = f"{price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
                out.append({
                    'obj': j,
                    'image_url': img,
                    'hover_url': hover,
                    'gallery': gallery,
                    'price': price,
                    'price_str': price_str,
                    'detail_url': f"/jewellery/{j.jewellery_product_id}/",  # replace with get_absolute_url if defined
                })
        return out

    context = {
        'most_selling': build_list_for_key(MOST_SELLING_KEY),
        'trending': build_list_for_key(TRENDING_KEY),
        'sale': build_list_for_key(SALE_KEY),
    }

    return render(request, 'shop/jewellery.html', context)


def jewellery_info(request, jewellery_product_id):
    """
    Jewellery product detail page by numeric jewellery_product_id.
    """
    jewellery = get_object_or_404(Jewellery, jewellery_product_id=jewellery_product_id)

    # placeholders
    placeholder = static('images/product-detail-page/product-placeholder.jpg')
    placeholder_hover = static('images/product-detail-page/product-placeholder-hover.jpg')

    # primary image
    image_url = jewellery.image.url if getattr(jewellery, 'image', None) and hasattr(jewellery.image, 'url') else placeholder
    # hover image fallback
    hover_url = (
        jewellery.image_hover.url
        if getattr(jewellery, 'image_hover', None) and hasattr(jewellery.image_hover, 'url')
        else image_url
    )

    # gallery
    gallery_images = []
    if getattr(jewellery, 'image', None) and hasattr(jewellery.image, 'url'):
        gallery_images.append(jewellery.image.url)
    if getattr(jewellery, 'image_hover', None) and hasattr(jewellery.image_hover, 'url'):
        if jewellery.image_hover.url not in gallery_images:
            gallery_images.append(jewellery.image_hover.url)
    if not gallery_images:
        gallery_images = [placeholder, placeholder_hover]

    # base price
    try:
        base_price = Decimal(str(jewellery.price))
    except Exception:
        base_price = Decimal('0.00')

    context = {
        'jewellery': jewellery,
        'image_url': image_url,
        'hover_url': hover_url,
        'gallery_images': gallery_images,
        'price': base_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'short_desc': jewellery.short_desc,
    }

    return render(request, 'shop/jewellery_info.html', context)


def bags(request):
    """
    Build three collection lists for the bags slider:
      - Most_selling
      - Trending
      - Sale

    Each bag item is enriched with:
      - image_url, hover_url, gallery list
      - price_str
      - detail_url (expects /bags/<id>/)
    """
    # placeholders
    placeholder = static('images/product-detail-page/product-placeholder.jpg')
    placeholder_hover = static('images/product-detail-page/product-placeholder-hover.jpg')

    # fetch all bags once
    all_bags = Bag.objects.all()

    # helper to get image urls safely
    def get_image_urls(obj):
        img = obj.image.url if getattr(obj, 'image', None) and hasattr(obj.image, 'url') else placeholder
        hover = obj.image_hover.url if getattr(obj, 'image_hover', None) and hasattr(obj.image_hover, 'url') else (img or placeholder_hover)
        gallery = []
        if getattr(obj, 'image', None) and hasattr(obj.image, 'url'):
            gallery.append(obj.image.url)
        if getattr(obj, 'image_hover', None) and hasattr(obj.image_hover, 'url') and obj.image_hover.url not in gallery:
            gallery.append(obj.image_hover.url)
        if not gallery:
            gallery = [placeholder, placeholder_hover]
        return img, hover, gallery

    # collections keys (as stored in MultiSelectField)
    MOST_SELLING_KEY = 'Most_selling'
    TRENDING_KEY     = 'Trending'
    SALE_KEY         = 'Sale'

    # helper to build enriched list for a given key
    def build_list_for_key(key):
        out = []
        for b in all_bags:
            if b.collection and key in (b.collection or []):
                img, hover, gallery = get_image_urls(b)
                try:
                    price = Decimal(str(b.price))
                except Exception:
                    price = Decimal('0.00')
                price_str = f"{price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
                out.append({
                    'obj': b,
                    'image_url': img,
                    'hover_url': hover,
                    'gallery': gallery,
                    'price': price,
                    'price_str': price_str,
                    'detail_url': f"/bags/{b.bag_product_id}/",
                })
        return out

    context = {
        'most_selling': build_list_for_key(MOST_SELLING_KEY),
        'trending': build_list_for_key(TRENDING_KEY),
        'sale': build_list_for_key(SALE_KEY),
    }

    return render(request, 'shop/bags.html', context)


def bags_info(request, bag_product_id):
    """
    Bag product detail page by numeric bag_product_id.
    """
    bag = get_object_or_404(Bag, bag_product_id=bag_product_id)

    # placeholders
    placeholder = static('images/product-detail-page/product-placeholder.jpg')
    placeholder_hover = static('images/product-detail-page/product-placeholder-hover.jpg')

    # primary image
    image_url = bag.image.url if getattr(bag, 'image', None) and hasattr(bag.image, 'url') else placeholder
    # hover image fallback
    hover_url = (
        bag.image_hover.url
        if getattr(bag, 'image_hover', None) and hasattr(bag.image_hover, 'url')
        else image_url
    )

    # gallery
    gallery_images = []
    if getattr(bag, 'image', None) and hasattr(bag.image, 'url'):
        gallery_images.append(bag.image.url)
    if getattr(bag, 'image_hover', None) and hasattr(bag.image_hover, 'url'):
        if bag.image_hover.url not in gallery_images:
            gallery_images.append(bag.image_hover.url)
    if not gallery_images:
        gallery_images = [placeholder, placeholder_hover]

    # base price
    try:
        base_price = Decimal(str(bag.price))
    except Exception:
        base_price = Decimal('0.00')

    context = {
        'bag': bag,
        'image_url': image_url,
        'hover_url': hover_url,
        'gallery_images': gallery_images,
        'price': base_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'short_desc': bag.desc,
    }

    return render(request, 'shop/bags_info.html', context)


def shoes(request):
    """
    Build three collection lists for the shoes slider:
      - Most_selling
      - Trending
      - Sale

    Each shoes item is enriched with:
      - image_url, hover_url, gallery list
      - price_str
      - detail_url (reverse name: 'shoes_info' expects pk)
    """
    # placeholders
    placeholder = static('images/product-detail-page/product-placeholder.jpg')
    placeholder_hover = static('images/product-detail-page/product-placeholder-hover.jpg')

    # fetch all shoes items once
    all_shoes = Shoes.objects.all()

    # helper to get image urls safely
    def get_image_urls(obj):
        img = obj.image.url if getattr(obj, 'image', None) and hasattr(obj.image, 'url') else placeholder
        hover = obj.image_hover.url if getattr(obj, 'image_hover', None) and hasattr(obj.image_hover, 'url') else (img or placeholder_hover)
        gallery = []
        if getattr(obj, 'image', None) and hasattr(obj.image, 'url'):
            gallery.append(obj.image.url)
        if getattr(obj, 'image_hover', None) and hasattr(obj.image_hover, 'url') and obj.image_hover.url not in gallery:
            gallery.append(obj.image_hover.url)
        if not gallery:
            gallery = [placeholder, placeholder_hover]
        return img, hover, gallery

    # collections keys (as stored in CharField choices)
    MOST_SELLING_KEY = 'Most_Selling'
    TRENDING_KEY = 'Trending'
    SALE_KEY = 'Sale'

    # helper to build enriched list for a given key
    def build_list_for_key(key):
        out = []
        for s in all_shoes:
            if s.collection and key == s.collection:
                img, hover, gallery = get_image_urls(s)
                try:
                    price = Decimal(str(s.price))
                except Exception:
                    price = Decimal('0.00')
                price_str = f"{price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
                out.append({
                    'obj': s,
                    'image_url': img,
                    'hover_url': hover,
                    'gallery': gallery,
                    'price': price,
                    'price_str': price_str,
                    'detail_url': f"/shoes/{s.shoes_product_id}/",  # matches jewellery/bags pattern
                })
        return out

    context = {
        'most_selling': build_list_for_key(MOST_SELLING_KEY),
        'trending': build_list_for_key(TRENDING_KEY),
        'sale': build_list_for_key(SALE_KEY),
    }

    return render(request, 'shop/shoes.html', context)


def shoes_info(request, shoes_product_id):
    """
    Shoes product detail page by numeric shoes_product_id.
    """
    shoes = get_object_or_404(Shoes, shoes_product_id=shoes_product_id)

    # placeholders
    placeholder = static('images/product-detail-page/product-placeholder.jpg')
    placeholder_hover = static('images/product-detail-page/product-placeholder-hover.jpg')

    # primary image
    image_url = shoes.image.url if getattr(shoes, 'image', None) and hasattr(shoes.image, 'url') else placeholder
    # hover image fallback
    hover_url = (
        shoes.image_hover.url
        if getattr(shoes, 'image_hover', None) and hasattr(shoes.image_hover, 'url')
        else image_url
    )

    # gallery
    gallery_images = []
    if getattr(shoes, 'image', None) and hasattr(shoes.image, 'url'):
        gallery_images.append(shoes.image.url)
    if getattr(shoes, 'image_hover', None) and hasattr(shoes.image_hover, 'url'):
        if shoes.image_hover.url not in gallery_images:
            gallery_images.append(shoes.image_hover.url)
    if not gallery_images:
        gallery_images = [placeholder, placeholder_hover]

    # base price
    try:
        base_price = Decimal(str(shoes.price))
    except Exception:
        base_price = Decimal('0.00')

    context = {
        'shoes': shoes,
        'image_url': image_url,
        'hover_url': hover_url,
        'gallery_images': gallery_images,
        'price': base_price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
        'desc': shoes.desc,
    }

    return render(request, 'shop/shoes_info.html', context)


def faqs(request):
    return render(request, 'shop/faqs.html')


def about_us(request):
    return render(request, 'shop/about_us.html')


def Collections(request):
    return render(request, 'shop/Collections.html')


def contact_view(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message_text = request.POST.get('message', '').strip()

        # Basic required check
        if name and email and message_text:
            ContactMessage.objects.create(
                name=name, email=email, phone=phone, subject=subject, message=message_text
            )
            messages.success(request, "✅ Your message has been sent.")
            return redirect('contact')
        else:
            messages.error(request, "Please fill in the required fields.")
    return render(request, 'shop/contact.html')


def order_view(request):
    customer_id = request.session.get('customer_id')

    # If no customer logged in, show empty orders
    if not customer_id:
        return render(request, 'shop/orders.html', {'orders': []})

    # Fetch all orders for this customer (newest first)
    orders_qs = CustomerOrder.objects.filter(customer_id=customer_id).order_by('-created_at')

    # Prepare list with parsed JSON order_items
    orders = []
    for order in orders_qs:
        items = order.order_items
        if isinstance(items, str):  # if stored as JSON string
            try:
                items = json.loads(items)
            except json.JSONDecodeError:
                items = []
        # ensure it's a list
        if not isinstance(items, list):
            items = [items]

        # normalize each item (so we can use item.name, etc.)
        normalized_items = []
        for it in items:
            normalized_items.append({
                'name': it.get('product_name') or it.get('name') or '',
                'price': it.get('price', 0),
                'size': it.get('size', '-'),
                'quantity': it.get('quantity', 0),
                'subtotal': it.get('subtotal', 0),
            })

        orders.append({
            'created_at': order.created_at,
            'total_price': order.total_price,
            'order_items': normalized_items,
        })

    return render(request, 'shop/orders.html', {'orders': orders})


    if request.method == "POST":
        customer_id = request.session.get('customer_id')
        if not customer_id:
            messages.warning(request, "Please log in to add items to your wishlist.")
            return redirect('login')

        # Get product type and ID dynamically
        product_id = (
            request.POST.get('product_id') or
            request.POST.get('cosmetic_product_id') or
            request.POST.get('jewellery_product_id') or
            request.POST.get('shoes_product_id') or
            request.POST.get('bag_product_id')
        )

        if not product_id:
            messages.error(request, "Invalid product.")
            return redirect('home')  # or any fallback page

        title = request.POST.get('title')
        price = request.POST.get('price')
        image_url = request.POST.get('image_url')
        hover_url = request.POST.get('hover_url')

        # Avoid duplicates
        wishlist_item, created = Wishlist.objects.get_or_create(
            customer_id=customer_id,
            product_id=product_id,
            defaults={
                'title': title,
                'price': price,
                'image_url': image_url,
                'hover_url': hover_url
            }
        )

        if created:
            messages.success(request, f"'{title}' added to your wishlist ❤️")
        else:
            messages.info(request, f"'{title}' is already in your wishlist.")

        return redirect('wishlist')

# ---- Wishlist related views ----
# single canonical mapping used by both views:
# model, model_id_field_name_on_model, detail_url_template (use {id})
CATEGORY_MAP = {
    'product':   (Product,   'product_id',          '/product/{id}/'),
    'cosmetic':  (Cosmetic,  'cosmetic_product_id', '/cosmetic/{id}/'),
    'jewellery': (Jewellery, 'jewellery_product_id','/jewellery/{id}/'),
    'shoes':     (Shoes,     'shoes_product_id',    '/shoes/{id}/'),
    'bags':       (Bag,       'bag_product_id',      '/bags/{id}/'),
}

# ---- add_to_wishlist view ----
def add_to_wishlist(request, category, item_id):
    """
    POST endpoint: /add-to-wishlist/<category>/<item_id>/
    Stores product info into Wishlist model using `item_product_id` field.
    """
    if request.method != "POST":
        return redirect('index')

    customer_id = request.session.get('customer_id')
    if not customer_id:
        messages.warning(request, "Please log in to add items to your wishlist.")
        return redirect('login')

    model_info = CATEGORY_MAP.get(category)
    if not model_info:
        messages.error(request, "Invalid category.")
        return redirect('index')

    model, model_id_field, _ = model_info

    # Fetch object (404 if missing)
    obj = get_object_or_404(model, **{model_id_field: item_id})

    # Extract fields preferring model fields, falling back to POST hidden inputs (if provided)
    title = getattr(obj, 'title', None) or getattr(obj, 'name', '') or request.POST.get('title', '')
    price_val = getattr(obj, 'price', None) or request.POST.get('price', 0)
    # Normalize price to Decimal
    try:
        price = Decimal(str(price_val))
    except Exception:
        price = Decimal('0.00')

    # image / hover fields — support ImageField (.url) or raw URL in POST
    image_field = getattr(obj, 'image', None)
    if image_field and hasattr(image_field, 'url'):
        image_url = image_field.url
    else:
        image_url = request.POST.get('image_url', '') or ''

    hover_field = getattr(obj, 'image_hover', None) or getattr(obj, 'image_hover_url', None)
    if hover_field and hasattr(hover_field, 'url'):
        hover_url = hover_field.url
    else:
        hover_url = request.POST.get('hover_url', '') or request.POST.get('image_hover', '') or ''

    # Save into Wishlist — note: your model uses item_product_id and has a category field
    wishlist_item, created = Wishlist.objects.get_or_create(
        customer_id=customer_id,
        category=category,
        item_product_id=item_id,
        defaults={
            'title': title,
            'price': price,
            'image_url': image_url,
            'hover_url': hover_url,
        }
    )

    if created:
        messages.success(request, f"'{title}' added to your wishlist ❤️")
    else:
        messages.info(request, f"'{title}' is already in your wishlist.")

    return redirect('wishlist_view')  # or 'wishlist_view' depending on your URL name


# ---- wishlist_view ----
def wishlist_view(request):
    """
    Shows the user's wishlist. Returns enriched items with:
    id, category, product_id (item_product_id), title, price (string), image_url, hover_url, detail_url
    """
    customer_id = request.session.get('customer_id')
    if not customer_id:
        messages.warning(request, "Please log in to view your wishlist.")
        return redirect('login')

    raw_items = Wishlist.objects.filter(customer_id=customer_id).order_by('-created_at')

    enriched = []
    for w in raw_items:
        # basic values from wishlist row
        title = w.title or ''
        price = (w.price if w.price is not None else Decimal('0.00'))
        image = w.image_url or ''
        hover = w.hover_url or image

        product_id = getattr(w, 'item_product_id', None)

        # build default fallback detail_url
        detail_url = "/"
        if w.category and product_id:
            detail_url = f"/{w.category}/{product_id}/"
        elif product_id:
            detail_url = f"/product/{product_id}/"

        # try to enrich from product model if we have a mapping and product_id
        model_info = CATEGORY_MAP.get((w.category or 'product'))
        if model_info and product_id:
            model, model_id_field, detail_template = model_info
            # try to fetch product object (safe .filter().first())
            obj = model.objects.filter(**{model_id_field: product_id}).first()
            if obj:
                # fill missing data from product object
                if not title:
                    title = getattr(obj, 'title', None) or getattr(obj, 'name', '') or title
                if not image:
                    img_field = getattr(obj, 'image', None)
                    if img_field and hasattr(img_field, 'url'):
                        image = img_field.url
                if not hover:
                    hover_field = getattr(obj, 'image_hover', None)
                    if hover_field and hasattr(hover_field, 'url'):
                        hover = hover_field.url
                # prefer object's price if wishlist row had zero/empty
                try:
                    obj_price = Decimal(str(getattr(obj, 'price', '0') or '0'))
                    if obj_price and (not price or Decimal(price) == Decimal('0.00')):
                        price = obj_price
                except Exception:
                    pass
                # build detail url from template
                try:
                    detail_url = detail_template.format(id=product_id)
                except Exception:
                    detail_url = f"/{w.category}/{product_id}/"

        # ensure price string formatted
        try:
            price_str = f"{Decimal(price).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):.2f}"
        except Exception:
            price_str = "0.00"

        enriched.append({
            'id': w.id,
            'category': w.category,
            'product_id': product_id,
            'title': title,
            'price': price_str,
            'image_url': image,
            'hover_url': hover or image,
            'detail_url': detail_url,
        })

    return render(request, 'shop/wishlist.html', {'wishlist_items': enriched})


def remove_from_wishlist(request, wishlist_id):
    customer_id = request.session.get('customer_id')
    if not customer_id:
        messages.warning(request, "Please log in first.")
        return redirect('login')

    wishlist_item = get_object_or_404(Wishlist, id=wishlist_id, customer_id=customer_id)
    wishlist_item.delete()
    messages.success(request, "Item removed from your wishlist.")
    return redirect('wishlist_view')






