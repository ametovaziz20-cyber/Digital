from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    Cart, Category, City, Customer, Delivery, Favorite,
    Order, Product, ProductCart, ProductOrder, Region,
)


class ShopTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='shopper', password='StrongPassword987!',
            first_name='Тест', last_name='Покупатель', email='shopper@example.com',
        )
        self.customer = Customer.objects.create(user=self.user, phone='+998901112233')
        self.category = Category.objects.create(title='Телефоны', slug='phones')
        self.product = Product.objects.create(
            title='Телефон', slug='test-phone', descr='Тестовый телефон',
            price=100000, discount=10, quantity=3, category=self.category,
        )
        self.region = Region.objects.create(name='Тестовый регион')
        self.city = City.objects.create(name='Тестовый город', region=self.region)

    def login(self):
        self.client.force_login(self.user)

    def test_public_pages(self):
        for url in [reverse('index'), reverse('login'), reverse('register'),
                    reverse('category', args=['phones']),
                    reverse('product', args=['test-phone']),
                    reverse('search') + '?q=телефон']:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_registration_creates_customer(self):
        response = self.client.post(reverse('register'), {
            'username': 'newclient', 'first_name': 'Новый',
            'last_name': 'Клиент', 'email': 'newclient@example.com',
            'phone_number': '+998901234567',
            'password1': 'TestPassword987!', 'password2': 'TestPassword987!',
        })
        self.assertRedirects(response, reverse('index'))
        self.assertTrue(Customer.objects.filter(user__username='newclient').exists())

    def test_cart_requires_login_and_post(self):
        url = reverse('add_to_cart', args=[self.product.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.login()
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertFalse(ProductCart.objects.exists())

    def test_add_update_and_clear_cart(self):
        self.login()
        url = reverse('add_to_cart', args=[self.product.pk])
        self.client.post(url)
        self.client.post(url)
        item = ProductCart.objects.get()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.get_total_price, 180000)
        self.assertEqual(self.client.get(reverse('cart')).status_code, 200)
        item_url = reverse('change_cart_quantity', args=[item.pk])
        self.client.post(item_url, {'action': 'increase'})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
        self.client.post(url)  # cannot exceed stock
        item.refresh_from_db()
        self.assertEqual(item.quantity, 3)
        self.client.post(item_url, {'action': 'decrease'})
        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)
        self.client.post(reverse('clear_cart'))
        self.assertFalse(ProductCart.objects.exists())

    def test_favorites(self):
        self.login()
        url = reverse('toggle_favorite', args=[self.product.pk])
        self.client.post(url)
        self.assertEqual(Favorite.objects.count(), 1)
        self.assertEqual(self.client.get(reverse('favorites')).status_code, 200)
        self.client.post(url)
        self.assertEqual(Favorite.objects.count(), 0)

    def test_checkout_creates_order_and_clears_cart(self):
        self.login()
        cart = Cart.objects.create(customer=self.customer)
        ProductCart.objects.create(cart=cart, product=self.product, quantity=2)
        data = {
            'region': self.region.pk, 'city': self.city.pk,
            'street': 'Тестовая', 'home': '5', 'flat': '3',
            'phone': '+998901112233', 'comment': 'Позвонить',
            'first_name': 'Тест', 'last_name': 'Покупатель', 'email': 'shopper@example.com',
        }
        self.assertEqual(self.client.get(reverse('checkout')).status_code, 200)
        response = self.client.post(reverse('checkout'), data)
        self.assertEqual(response.status_code, 302)
        order = Order.objects.get()
        self.assertRedirects(response, reverse('order_success', args=[order.pk]))
        self.assertEqual(order.price, 180000)
        self.assertEqual(ProductOrder.objects.get().price, 90000)
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 1)
        self.assertFalse(ProductCart.objects.filter(cart=cart).exists())
        self.assertEqual(self.client.get(reverse('orders')).status_code, 200)
        self.assertEqual(self.client.get(reverse('order_success', args=[order.pk])).status_code, 200)
        self.assertEqual(self.client.post(reverse('checkout'), data).status_code, 302)
        self.assertEqual(Order.objects.count(), 1)

    def test_invalid_checkout_city(self):
        self.login()
        cart = Cart.objects.create(customer=self.customer)
        ProductCart.objects.create(cart=cart, product=self.product, quantity=1)
        other_region = Region.objects.create(name='Другой регион')
        other_city = City.objects.create(name='Другой город', region=other_region)
        response = self.client.post(reverse('checkout'), {
            'region': self.region.pk, 'city': other_city.pk,
            'street': 'Тестовая', 'home': '1', 'phone': '+998901112233',
            'first_name': 'Тест', 'last_name': 'Тест',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.assertEqual(self.product.quantity, 3)

    def test_insufficient_stock(self):
        self.login()
        cart = Cart.objects.create(customer=self.customer)
        ProductCart.objects.create(cart=cart, product=self.product, quantity=5)
        response = self.client.post(reverse('checkout'), {
            'region': self.region.pk, 'city': self.city.pk,
            'street': 'Тестовая', 'home': '1', 'phone': '+998901112233',
            'first_name': 'Тест', 'last_name': 'Тест',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Order.objects.exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.quantity, 3)

    def test_other_customer_cannot_view_order(self):
        self.login()
        delivery = Delivery.objects.create(
            customer=self.customer, region=self.region, city=self.city,
            phone='+998901112233', street='A', home='1',
        )
        order = Order.objects.create(customer=self.customer, delivery=delivery, price=100000)
        other = User.objects.create_user(username='another', password='TestPassword987!')
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse('order_success', args=[order.pk])).status_code, 404)
