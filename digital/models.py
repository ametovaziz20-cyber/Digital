from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Category(models.Model):
    title = models.CharField(max_length=150, unique=True, verbose_name='Название')
    icon = models.ImageField(upload_to='icons/', null=True, blank=True, verbose_name='Иконка')
    slug = models.SlugField(unique=True, verbose_name='Слаг')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('category', kwargs={'slug': self.slug})


class ProductDictionary(models.Model):
    name = models.CharField(max_length=100, verbose_name='Название')
   
    class Meta:
        verbose_name = 'Словарь'
        verbose_name_plural = 'Словари'
    
    def __str__(self):
        return self.name

class Product(models.Model):
    title = models.CharField(max_length=150, verbose_name='Название товара')
    brand = models.CharField(max_length=100, blank=True, db_index=True, verbose_name='Бренд')
    slug = models.SlugField(unique=True, verbose_name='Слаг товара')
    descr = models.CharField(max_length=400, verbose_name='Описание')
    price = models.IntegerField(default=1000, validators=[MinValueValidator(0)], verbose_name='Стоимость товара')
    discount = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(100)], verbose_name='Скидка')
    quantity = models.IntegerField(default=15, validators=[MinValueValidator(0)], verbose_name='Количество товара')
    is_popular = models.BooleanField(default=False, verbose_name='Хит продаж')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='Категрия товара', related_name='products')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
    
    def __str__(self):
        return self.title
    
    def first_photo(self):
        image = self.images.first()
        return image.photo.url if image and image.photo else ''

    def get_price(self):
        if self.discount:
            p = self.price - (self.price * self.discount / 100)
        else:
            p = self.price

        return int(p)
    
    def get_absolute_url(self):
        return reverse('product', kwargs={'slug': self.slug})
    
    
class ImagesProduct(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name='Товар'
    )

    color = models.ForeignKey(
        'ProductColor',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='images',
        verbose_name='Цвет товара'
    )

    photo = models.ImageField(
        upload_to='products/',
        verbose_name='Фото товара'
    )

    def __str__(self):
        return f'Фото товара {self.product.title}'

    class Meta:
        verbose_name = 'Фото товара'
        verbose_name_plural = 'Фото товаров'
   
    
class ProductSpec(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_specs', verbose_name='Товар')
    title = models.ForeignKey(ProductDictionary, on_delete=models.CASCADE, related_name='product_specs', verbose_name='Заголовок')
    value = models.CharField(max_length=150, verbose_name='Значение')
    
    class Meta:
        verbose_name = 'Характеристика'
        verbose_name_plural = 'Характеристики'
        
    def __str__(self):
        return self.title.name
    
class ProductColor(models.Model):
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='colors',
        verbose_name='Товар'
    )

    name = models.CharField(
        max_length=100,
        verbose_name='Название цвета'
    )

    hex_color = models.CharField(
        max_length=7,
        default='#FFFFFF',
        verbose_name='HEX цвета'
    )


    def __str__(self):
        return f'{self.product.title} — {self.name}'

    class Meta:
        verbose_name = 'Цвет товара'
        verbose_name_plural = 'Цвета товаров'
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'name'],
                name='unique_product_color'
            )
        ]

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    phone = models.CharField(max_length=40, verbose_name='Номер телефона')
    region = models.CharField(max_length=100, verbose_name='Регион', null=True, blank=True)
    city = models.CharField(max_length=100, verbose_name='Город', null=True, blank=True)
    street = models.CharField(max_length=100, verbose_name='Улица', null=True, blank=True)
    home = models.CharField(max_length=100, verbose_name='Дом', null=True, blank=True)
    flat = models.CharField(max_length=100, verbose_name='Квартира', null=True, blank=True)

    def __str__(self):
        return f'Покупатель {self.user.last_name} {self.user.first_name}'

    class Meta:
        verbose_name = 'Покупателя'
        verbose_name_plural = 'Покупатели'


class Favorite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')

    def __str__(self):
        return f'Товар {self.product.title} пользователя {self.user.last_name} {self.user.first_name}'

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        constraints = [models.UniqueConstraint(fields=['user', 'product'], name='unique_favorite_user_product')]
        

class Cart(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, verbose_name='Покупатель')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')


    class Meta:
        verbose_name = 'Корзину'
        verbose_name_plural = 'Корзины покупателей'
        
    def __str__(self):
        return f'Корзина №: {self.pk} покупателя {self.customer.user.last_name} {self.customer.user.first_name} на сумму {self.basket_price}'

    @property
    def basket_price(self):
        product_basket = self.products.all()
        price = sum([i.get_total_price for i in product_basket])  # [40, 100]
        return price

    @property
    def quantity_products(self):
        product_basket = self.products.all()
        quantity = sum([i.quantity for i in product_basket])  # [2, 1]
        return quantity

class ProductCart(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name='Товар')
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, verbose_name='Корзина', related_name='products')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Кол-во')
    color = models.ForeignKey(
    ProductColor,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cart_items',
        verbose_name='Цвет товара'
    )
    added_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата добавления')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата изменения')

    def __str__(self):
        return f'Товар {self.product.title} в кол-ве {self.quantity} на сумму {self.get_total_price}'

    @property
    def get_total_price(self):
        return int(self.quantity * self.product.get_price())

    @property
    def get_old_price(self):
        return int(self.quantity * self.product.price)

    class Meta:
        verbose_name = 'Товар Корзины'
        verbose_name_plural = 'Товары Корзин'
        constraints = [
            models.UniqueConstraint(
                fields=['cart', 'product', 'color'],
                condition=models.Q(color__isnull=False),
                name='unique_cart_product_color'
            ),
            models.UniqueConstraint(
                fields=['cart', 'product'],
                condition=models.Q(color__isnull=True),
                name='unique_cart_product_no_color'
            )
        ]
        
        

# Регионы доставки
class Region(models.Model):
    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Название региона'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'
        ordering = ['name']


# Города доставки
class City(models.Model):
    name = models.CharField(
        max_length=150,
        verbose_name='Название города'
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.CASCADE,
        related_name='cities',
        verbose_name='Регион'
    )

    def __str__(self):
        return f'{self.name} ({self.region.name})'

    class Meta:
        verbose_name = 'Город'
        verbose_name_plural = 'Города'
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['region', 'name'],
                name='unique_region_city'
            )
        ]


class Delivery(models.Model):
    first_name = models.CharField(max_length=150, blank=True, default='', verbose_name='Имя получателя')
    last_name = models.CharField(max_length=150, blank=True, default='', verbose_name='Фамилия получателя')
    email = models.EmailField(blank=True, verbose_name='Электронная почта')

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='deliveries',
        verbose_name='Покупатель'
    )

    phone = models.CharField(
        max_length=40,
        verbose_name='Телефон получателя'
    )

    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий к доставке'
    )

    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        verbose_name='Регион'
    )

    city = models.ForeignKey(
        City,
        on_delete=models.PROTECT,
        verbose_name='Город'
    )

    street = models.CharField(
        max_length=150,
        verbose_name='Улица'
    )

    home = models.CharField(
        max_length=50,
        verbose_name='Дом'
    )

    flat = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Квартира'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    def __str__(self):
        return f'Доставка №{self.pk} — {self.city.name}'

    class Meta:
        verbose_name = 'Доставка'
        verbose_name_plural = 'Доставки'


# Заказ
class Order(models.Model):

    class Status(models.TextChoices):
        NEW = 'new', 'Новый'
        CONFIRMED = 'confirmed', 'Подтверждён'
        PROCESSING = 'processing', 'В обработке'
        SHIPPING = 'shipping', 'В доставке'
        DELIVERED = 'delivered', 'Доставлен'
        COMPLETED = 'completed', 'Завершён'
        CANCELLED = 'cancelled', 'Отменён'

    customer = models.ForeignKey(
        Customer,
        on_delete=models.PROTECT,
        related_name='orders',
        verbose_name='Покупатель'
    )

    delivery = models.OneToOneField(
        Delivery,
        on_delete=models.PROTECT,
        related_name='order',
        verbose_name='Доставка'
    )

    price = models.PositiveBigIntegerField(
        default=0,
        verbose_name='Стоимость заказа'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
        verbose_name='Статус заказа'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    def __str__(self):
        return f'Заказ №{self.pk} — {self.customer}'

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']


class ProductOrder(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='Заказ'
    )
    color_name = models.CharField(
        max_length=100,
        blank=True,
        default='',
        verbose_name='Цвет товара'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='order_items',
        verbose_name='Товар'
    )

    title = models.CharField(
        max_length=150,
        verbose_name='Название товара'
    )

    slug = models.CharField(
        max_length=150,
        verbose_name='Слаг товара'
    )

    price = models.PositiveBigIntegerField(
        verbose_name='Цена за единицу'
    )

    quantity = models.PositiveIntegerField(
        verbose_name='Количество'
    )

    total_price = models.PositiveBigIntegerField(
        verbose_name='Общая стоимость'
    )

    photo = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Путь к фотографии'
    )

    def __str__(self):
        return f'{self.title} × {self.quantity}'

    class Meta:
        verbose_name = 'Товар заказа'
        verbose_name_plural = 'Товары заказа'