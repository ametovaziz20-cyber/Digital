
from django.contrib import admin
from django.utils.safestring import mark_safe

from django.utils.html import format_html
from .forms import *
from .models import *

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('title', )}
    form = CategoryForm
    list_display = ('pk', 'title', 'get_icon')
    list_display_links = ('pk', 'title')

    def get_icon(self, obj):
        if obj.icon:
            try:
                return mark_safe(f'<img src="{obj.icon.url}" width="30" >')  # Функция для отправки тегов
            except:
                return 'No icon'
        else:
            return 'No icon'

    get_icon.short_description = 'Иконка'
    

class ImagesProductInline(admin.TabularInline):
    model = ImagesProduct
    extra = 1
    form = ImagesProductInlineForm
    fields = ('photo', 'color')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.pk and obj.photo:
            return format_html(
                '<img src="{}" style="width:100px;height:100px;object-fit:contain;" />',
                obj.photo.url
            )
        return "Нет изображения"

    image_preview.short_description = 'Предпросмотр'


class ProductSpecInline(admin.TabularInline):
    model = ProductSpec
    extra = 1
    autocomplete_fields = ('title',)

class ProductColorInline(admin.TabularInline):
    model = ProductColor
    extra = 1
    fields = ('name', 'hex_color')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'image_preview',
        'title',
        'brand',
        'category',
        'price',
        'discount',
        'discounted_price',
        'quantity',
        'is_popular',
        'created_at',
    )

    list_display_links = ('id', 'title')

    list_editable = ('is_popular',)

    list_filter = (
        'category',
        'is_popular',
        'created_at',
        'updated_at',
    )

    search_fields = (
        'title',
        'slug',
        'descr',
    )

    prepopulated_fields = {
        'slug': ('title',)
    }

    readonly_fields = (
        'created_at',
        'updated_at',
        'image_preview',
        'discounted_price',
    )

    list_per_page = 20

    ordering = ('-created_at',)

    inlines = [ImagesProductInline, ProductSpecInline, ProductColorInline]

    fieldsets = (
        ('Основная информация', {
            'fields': (
                'title',
                'brand',    
                'slug',
                'category',
                'descr',
                'is_popular',
            )
        }),

        ('Цена и остатки', {
            'fields': (
                'price',
                'discount',
                'discounted_price',
                'quantity',
            )
        }),

        ('Изображение', {
            'fields': (
                'image_preview',
            )
        }),

        ('Дополнительная информация', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Фото')
    def image_preview(self, obj):
        if obj.pk:
            image = obj.images.first()

            if image and image.photo:
                return format_html(
                    '<img src="{}" style="width:60px;height:60px;object-fit:contain;border-radius:6px;" />',
                    image.photo.url
                )

        return "Нет фото"

    @admin.display(description='Цена со скидкой')
    def discounted_price(self, obj):
        if obj.pk:
            return f'{obj.get_price():,} сум'.replace(',', ' ')

        return '—'

@admin.register(ProductDictionary)
class ProductDictionaryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(ImagesProduct)
class ImagesProductAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'product',
        'image_preview',
    )

    list_filter = ('product',)
    search_fields = ('product__title',)
    autocomplete_fields = ('product',)

    @admin.display(description='Фото')
    def image_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:70px;height:70px;object-fit:contain;" />',
                obj.photo.url
            )
        return 'Нет фото'


@admin.register(ProductSpec)
class ProductSpecAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'product',
        'title',
        'value',
    )

    list_filter = ('title',)
    search_fields = (
        'product__title',
        'title__name',
        'value',
    )

    autocomplete_fields = (
        'product',
        'title',
    )




@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(City)
class CityAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'region')
    list_filter = ('region',)
    search_fields = ('name', 'region__name')
    autocomplete_fields = ('region',)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer',
        'phone',
        'region',
        'city',
        'street',
        'home',
        'created_at',
    )

    list_filter = ('region', 'city', 'created_at')
    search_fields = (
        'customer__user__username',
        'phone',
        'street',
    )

    readonly_fields = ('created_at',)
    autocomplete_fields = ('region', 'city')


class ProductOrderInline(admin.TabularInline):
    model = ProductOrder
    extra = 0

    fields = (
        'product',
        'title',
        'price',
        'quantity',
        'total_price',
    )

    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'customer',
        'price',
        'status',
        'created_at',
    )

    list_display_links = ('id', 'customer')
    list_editable = ('status',)

    list_filter = ('status', 'created_at')

    search_fields = (
        'id',
        'customer__user__username',
        'customer__user__first_name',
        'customer__user__last_name',
    )

    readonly_fields = (
        'customer',
        'delivery',
        'price',
        'created_at',
        'updated_at',
    )

    ordering = ('-created_at',)
    list_per_page = 25

    inlines = (ProductOrderInline,)

    fieldsets = (
        ('Информация о заказе', {
            'fields': (
                'customer',
                'delivery',
                'price',
                'status',
            )
        }),

        ('Даты', {
            'fields': (
                'created_at',
                'updated_at',
            )
        }),
    )

    def has_add_permission(self, request):
        return False


@admin.register(ProductOrder)
class ProductOrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'order',
        'title',
        'price',
        'quantity',
        'total_price',
    )

    search_fields = ('title', 'order__id')

    readonly_fields = (
        'order',
        'product',
        'title',
        'slug',
        'price',
        'quantity',
        'total_price',
        'photo',
    )

    def has_add_permission(self, request):
        return False


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'phone', 'region', 'city')
    search_fields = ('user__username', 'user__first_name', 'phone')


class ProductCartInline(admin.TabularInline):
    model = ProductCart
    extra = 0
    autocomplete_fields = ('product',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'basket_price', 'quantity_products', 'created_at')
    search_fields = ('customer__user__username',)
    inlines = (ProductCartInline,)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product', 'created_at')
    search_fields = ('user__username', 'product__title')
