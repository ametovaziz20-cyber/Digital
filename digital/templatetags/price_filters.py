
from django import template
from digital.utils import format_price

register = template.Library()


@register.filter
def price_format(value):
    return format_price(value)


@register.filter
def in_favorites(product_id, favorite_ids):
    return product_id in favorite_ids