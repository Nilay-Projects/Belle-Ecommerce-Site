# shop/urls.py
from django.urls import path
from . import views

# app_name = 'shop'

urlpatterns = [

    path('sign_up/', views.sign_up, name='sign_up'),

    path('login', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),  

    path('index/', views.index, name='index'),
    path('product/<int:pk>/', views.product_info, name='product_info'), 

    path('add-to-cart/<str:category>/<int:item_id>/', views.add_to_cart, name='add_to_cart'),

    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/update/', views.update_cart, name='update_cart'),
    path('cart/remove/<str:key>/', views.remove_from_cart, name='remove_from_cart'),

    path('checkout/', views.checkout, name='checkout'),

    path('women_shop/', views.women_shop, name='women_shop'),
    path('men_shop/', views.men_shop, name='men_shop'),

    path('cosmetic/', views.cosmetic, name='cosmetic'),
    path('cosmetics/<int:cosmetic_product_id>/', views.cosmetic_info, name='cosmetic_info'),

    path('jewellery/', views.jewellery, name='jewellery'),
    path('jewellery/<int:jewellery_product_id>/', views.jewellery_info, name='jewellery_info'),
    
    path('bags/', views.bags, name='bags'),
    path('bags/<int:bag_product_id>/', views.bags_info, name='bags_info'),

    path('shoes/', views.shoes, name='shoes'),
    path('shoes/<int:shoes_product_id>/', views.shoes_info, name='shoes_info'),

    path('faqs/', views.faqs, name='faqs'),
    path('about_us/', views.about_us, name='about_us'),
    path('contact/', views.contact_view, name='contact'),
    path('Collections/', views.Collections, name='Collections'),

    path('orders/', views.order_view, name='Orders'),

    path('wishlist/', views.wishlist_view, name='wishlist_view'),
    # path('add-to-wishlist/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('add-to-wishlist/<str:category>/<int:item_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:wishlist_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),

]




