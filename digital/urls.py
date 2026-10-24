from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('category/<slug:slug>/', views.category_detail, name='category'),
    path('product/<slug:slug>/', views.product_detail, name='product'),
    path('search/', views.search_products, name='search'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('cart/', views.cart_detail, name='cart'),
    path('cart/add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/item/<int:item_id>/', views.change_cart_quantity, name='change_cart_quantity'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('favorites/', views.favorites_view, name='favorites'),
    path('favorites/toggle/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('orders/', views.orders_view, name='orders'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/cities/', views.checkout_cities, name='checkout_cities'),
    path('orders/<int:order_id>/success/', views.order_success, name='order_success'),
    path('orders/<int:order_id>/pay/', views.create_stripe_checkout, name='stripe_checkout'),
]
