from decimal import Decimal, InvalidOperation


def format_price(price):
    try:
        number = Decimal(str(price))
        return f"{number:,.1f}".replace(",", " ")
    except (ValueError, TypeError, InvalidOperation):
        return "0.0"