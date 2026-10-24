from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q, IntegerField, ExpressionWrapper, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST
from django.core.files.storage import default_storage
from .forms import CheckoutForm, LoginForm, ProfileForm, RegisterForm
from .models import *
from django.core.paginator import Paginator
from django.utils.http import url_has_allowed_host_and_scheme
import stripe
from django.conf import settings
from django.urls import reverse

def get_favorite_ids(request):
    if not request.user.is_authenticated:
        return set()

    return set(
        Favorite.objects.filter(
            user=request.user
        ).values_list('product_id', flat=True)
    )


def index(request):
    products = Product.objects.prefetch_related('images')

    return render(request, 'digital/main.html', {
        'hits': products.filter(is_popular=True).order_by('-created_at')[:4],
        'new_products': products.order_by('-created_at')[:4],
        'favorite_ids': get_favorite_ids(request),
    })


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)

    all_products = Product.objects.filter(category=category)

    brands = (
        all_products
        .exclude(brand='')
        .order_by('brand')
        .values_list('brand', flat=True)
        .distinct()
    )

    brand = request.GET.get('brand', '').strip()
    model = request.GET.get('model', '').strip()
    price_from = request.GET.get('price_from', '').strip()
    price_till = request.GET.get('price_till', '').strip()

    products = all_products.prefetch_related('images')

    if brand:
        products = products.filter(brand__iexact=brand)

    if model:
        products = products.filter(title__icontains=model)

    products = products.annotate(
        final_price=ExpressionWrapper(
            F('price') * (100 - F('discount')) / 100,
            output_field=IntegerField()
        )
    )

    if price_from.isdigit():
        products = products.filter(
            final_price__gte=int(price_from)
        )

    if price_till.isdigit():
        products = products.filter(
            final_price__lte=int(price_till)
        )

    products = products.order_by('-created_at', '-id')

    paginator = Paginator(products, 4)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    favorite_ids = get_favorite_ids(request)
    
    return render(request, 'digital/category.html', {
        'category': category,
        'products': page_obj,
        'page_obj': page_obj,
        'brands': brands,
        'selected_brand': brand,
        'selected_model': model,
        'price_from': price_from,
        'price_till': price_till,
        'favorite_ids': favorite_ids,
    })



def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects
        .select_related('category')
        .prefetch_related('images', 'colors__images', 'product_specs__title'),
        slug=slug
    )

    related_products = (
        Product.objects
        .filter(category=product.category)
        .exclude(pk=product.pk)
        .prefetch_related('images')
        .order_by('-created_at')[:4]
    )

    colors = list(product.colors.all())
    all_images = list(product.images.all())

    general_images = [
        image.photo.url for image in all_images
        if image.photo and image.color_id is None
    ]

    galleries = {}
    for color in colors:
        color_images = [
            image.photo.url for image in color.images.all()
            if image.photo
        ]
        galleries[str(color.pk)] = color_images or general_images

    if colors:
        initial_images = galleries[str(colors[0].pk)]
    else:
        initial_images = [image.photo.url for image in all_images if image.photo]

    favorite_ids = get_favorite_ids(request)

    return render(request, 'digital/product_detail.html', {
        'product': product,
        'colors': colors,
        'galleries': galleries,
        'initial_images': initial_images,
        'related_products': related_products,
        'is_favorite': product.pk in favorite_ids,
        'favorite_ids': favorite_ids,
    })



def search_products(request):
    query = request.GET.get('q', '').strip()

    if query:
        products = (
            Product.objects
            .filter(
                Q(title__icontains=query) |
                Q(descr__icontains=query)
            )
            .prefetch_related('images')
            .order_by('-created_at')
        )
    else:
        products = Product.objects.none()

    return render(request, 'digital/products.html', {
        'products': products,
        'query': query,
        'favorite_ids': get_favorite_ids(request),
    })



def register_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save()
            Customer.objects.create(user=user, phone=form.cleaned_data['phone_number'])
        login(request, user)
        return redirect('index')
    return render(request, 'digital/register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('index')
    form = LoginForm(request=request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('index')
    return render(request, 'digital/login.html', {'form': form})


@login_required
@require_POST
def logout_view(request):
    logout(request)
    return redirect('index')


def get_customer(request):
    customer, _ = Customer.objects.get_or_create(user=request.user, defaults={'phone': ''})
    return customer



@login_required
def cart_detail(request):
    customer = get_customer(request)

    cart, _ = Cart.objects.get_or_create(
        customer=customer
    )

    items = (
        cart.products
        .select_related(
            'product',
            'color'
        )
        .prefetch_related(
            'product__images'
        )
        .order_by('-added_at')
    )

    return render(request, 'digital/cart.html', {
        'cart': cart,
        'cart_items': items,
    })



@login_required
@require_POST
def add_to_cart(request, product_id):
    with transaction.atomic():
        product = get_object_or_404(
            Product.objects.select_for_update(),
            pk=product_id
        )

        if product.quantity <= 0:
            messages.error(request, 'Товар закончился.')
            return redirect('product', slug=product.slug)

        color_id = request.POST.get('color_id')
        color = None

        if product.colors.exists():
            if color_id:
                color = get_object_or_404(
                    ProductColor,
                    pk=color_id,
                    product=product
                )
            else:
                # Карточки каталога пока не передают цвет.
                # Для них выбираем первый доступный.
                color = product.colors.order_by('id').first()

        elif color_id:
            messages.error(request, 'У товара нет такого цвета.')
            return redirect('product', slug=product.slug)

        cart, _ = Cart.objects.get_or_create(
            customer=get_customer(request)
        )

        total_in_cart = (
            ProductCart.objects
            .filter(cart=cart, product=product)
            .aggregate(total=Sum('quantity'))['total'] or 0
        )

        if total_in_cart >= product.quantity:
            messages.error(
                request,
                'Недостаточно товаров на складе.'
            )
            return redirect('cart')

        item, _ = ProductCart.objects.get_or_create(
            cart=cart,
            product=product,
            color=color,
            defaults={'quantity': 0}
        )

        ProductCart.objects.filter(pk=item.pk).update(
            quantity=F('quantity') + 1
        )

    messages.success(request, 'Товар добавлен в корзину.')
    return redirect('cart')



@login_required
@require_POST
def change_cart_quantity(request, item_id):
    action = request.POST.get('action')

    if action not in ('remove', 'increase', 'decrease'):
        return redirect('cart')

    with transaction.atomic():
        item = get_object_or_404(
            ProductCart.objects
            .select_related('cart', 'product'),
            pk=item_id,
            cart__customer__user=request.user
        )

        product = Product.objects.select_for_update().get(
            pk=item.product_id
        )

        if action == 'remove':
            item.delete()

        elif action == 'increase':
            total_in_cart = (
                ProductCart.objects
                .filter(
                    cart=item.cart,
                    product=product
                )
                .aggregate(total=Sum('quantity'))['total'] or 0
            )

            if total_in_cart >= product.quantity:
                messages.error(
                    request,
                    'Недостаточно товаров на складе.'
                )
                return redirect('cart')

            ProductCart.objects.filter(pk=item.pk).update(
                quantity=F('quantity') + 1
            )

        elif item.quantity <= 1:
            item.delete()

        else:
            ProductCart.objects.filter(pk=item.pk).update(
                quantity=F('quantity') - 1
            )

    return redirect('cart')



@login_required
@require_POST
def clear_cart(request):
    ProductCart.objects.filter(cart__customer__user=request.user).delete()
    messages.success(request, 'Корзина очищена.')
    return redirect('cart')


@login_required
@require_POST
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    favorite, created = Favorite.objects.get_or_create(
        user=request.user,
        product=product
    )

    if not created:
        favorite.delete()

    if request.POST.get('source') == 'favorites':
        return redirect('favorites')

    next_url = request.POST.get('next', '')

    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return redirect(next_url)

    return redirect('product', slug=product.slug)


@login_required
def favorites_view(request):
    products = (
        Product.objects
        .filter(favorite__user=request.user)
        .prefetch_related('images')
    )

    return render(request, 'digital/favorites.html', {
        'products': products,
        'favorite_ids': get_favorite_ids(request),
    })



@login_required
def profile_view(request):
    customer = get_customer(request)

    orders = (
        Order.objects
        .filter(customer=customer)
        .prefetch_related('products__product__images')
        .order_by('-created_at')
    )

    for order in orders:
        for item in order.products.all():
            item.photo_url = ''

            if item.photo:
                item.photo_url = default_storage.url(item.photo)

            elif item.product:
                image = item.product.images.first()

                if image and image.photo:
                    item.photo_url = image.photo.url

    return render(request, 'digital/profile.html', {
        'customer': customer,
        'orders': orders,
    })




@login_required
def profile_edit_view(request):
    customer = get_customer(request)

    form = ProfileForm(
        request.POST or None,
        instance=request.user,
        initial={'phone': customer.phone}
    )

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            form.save()

            customer.phone = form.cleaned_data['phone']
            customer.save(update_fields=['phone'])

        messages.success(request, 'Данные успешно сохранены.')
        return redirect('profile')

    return render(request, 'digital/profile_edit.html', {
        'form': form,
    })



@login_required
def orders_view(request):
    orders = Order.objects.filter(customer__user=request.user).prefetch_related('products')
    return render(request, 'digital/orders.html', {'orders': orders})


@require_GET
def checkout_cities(request):
    region = request.GET.get('region', '')
    cities = City.objects.filter(region_id=int(region)).values('id', 'name') if region.isdigit() else []
    return JsonResponse({'cities': list(cities)})



@login_required
def checkout(request):
    customer = get_customer(request)

    cart = Cart.objects.filter(customer=customer).first()

    if cart is None or not cart.products.exists():
        messages.warning(request, 'Сначала добавьте товары в корзину.')
        return redirect('cart')

    initial = {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'email': request.user.email,
        'phone': customer.phone,
    }

    form = CheckoutForm(request.POST or None, initial=initial)

    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                items = list(
                    cart.products
                    .select_related('product', 'color')
                    .order_by('pk')
                )

                if not items:
                    raise ValueError('Корзина пуста.')

                details = []
                total = 0

                for item in items:
                    product = item.product

                    if item.quantity <= 0:
                        raise ValueError('Некорректное количество товара.')

                    changed = Product.objects.filter(
                        pk=product.pk,
                        quantity__gte=item.quantity
                    ).update(
                        quantity=F('quantity') - item.quantity
                    )

                    if not changed:
                        raise ValueError(
                            f'Товар «{product.title}» закончился или его недостаточно.'
                        )

                    price = product.get_price()
                    line_total = price * item.quantity
                    total += line_total

                    color_name = item.color.name if item.color else ''

                    photo = None

                    if item.color:
                        photo = (
                            ImagesProduct.objects
                            .filter(product=product, color=item.color)
                            .first()
                        )

                    if photo is None:
                        photo = (
                            ImagesProduct.objects
                            .filter(product=product, color__isnull=True)
                            .first()
                        )

                    photo_path = photo.photo.name if photo and photo.photo else ''

                    details.append(
                        ProductOrder(
                            product=product,
                            title=product.title,
                            slug=product.slug,
                            price=price,
                            quantity=item.quantity,
                            total_price=line_total,
                            photo=photo_path,
                            color_name=color_name
                        )
                    )

                delivery = form.save(commit=False)
                delivery.customer = customer
                delivery.save()

                order = Order.objects.create(
                    customer=customer,
                    delivery=delivery,
                    price=total
                )

                for row in details:
                    row.order = order

                ProductOrder.objects.bulk_create(details)

                cart.products.all().delete()

            return redirect('stripe_checkout', order_id=order.pk)

        except ValueError as error:
            messages.error(request, str(error))

    items = cart.products.select_related('product', 'color')

    summary = [
        {
            'title': i.product.title,
            'quantity': i.quantity,
            'total': i.get_total_price
        }
        for i in items
    ]

    return render(request, 'digital/checkout.html', {
        'form': form,
        'cart_items': summary,
        'cart_total': sum(i['total'] for i in summary),
    })

@login_required
def create_stripe_checkout(request, order_id):
    order = get_object_or_404(
        Order,
        pk=order_id,
        customer__user=request.user
    )

    if order.is_paid:
        return redirect('order_success', order_id=order.pk)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    return_url = request.build_absolute_uri(
        reverse('order_success', args=[order.pk])
    )

    try:
        session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'rub',
                        'product_data': {
                            'name': f'Digitalstore — заказ №{order.pk}'
                        },
                        'unit_amount': int(order.price) * 100,
                    },
                    'quantity': 1,
                }
            ],
            client_reference_id=str(order.pk),
            metadata={
                'order_id': str(order.pk)
            },
            success_url=return_url + '?payment=success',
            cancel_url=return_url + '?payment=cancelled',
        )

        return redirect(session.url)

    except stripe.StripeError as error:
        print("STRIPE ERROR:", str(error))
    
        messages.error(
            request,
            'Не удалось открыть страницу оплаты Stripe.'
        )
        return redirect('order_success', order_id=order.pk)



@login_required
def order_success(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related('delivery', 'delivery__city', 'delivery__region')
        .prefetch_related('products'), pk=order_id, customer__user=request.user
    )
    return render(request, 'digital/order_success.html', {'order': order})


@login_required
def create_stripe_checkout(request, order_id):
    order = get_object_or_404(
        Order,
        pk=order_id,
        customer__user=request.user
    )

    if order.price <= 0:
        messages.error(request, 'Некорректная сумма заказа.')
        return redirect('order_success', order_id=order.id)

    if not settings.STRIPE_SECRET_KEY.startswith('sk_test_'):
        messages.error(request, 'Stripe Test Mode не настроен.')
        return redirect('order_success', order_id=order.id)

    stripe.api_key = settings.STRIPE_SECRET_KEY

    return_url = request.build_absolute_uri(
        reverse('order_success', args=[order.id])
    )

    try:
        session = stripe.checkout.Session.create(
            mode='payment',
            line_items=[
                {
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Digitalstore — заказ №{order.pk}'
                        },
                        'unit_amount': 100,
                    },
                    'quantity': 1,
                }
            ],
            client_reference_id=str(order.pk),
            metadata={
                'order_id': str(order.pk)
            },
            success_url=return_url + '?payment=success',
            cancel_url=return_url + '?payment=cancelled',
        )

        return redirect(session.url)

    except stripe.StripeError:
        messages.error(
            request,
            'Не удалось открыть страницу оплаты Stripe.'
        )
        return redirect('order_success', order_id=order.id)
