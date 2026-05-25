from django import template

register = template.Library()


@register.filter
def tr_num(value):
    try:
        if value is None:
            return '—'
        num = float(value)
        negative = num < 0
        formatted = f"{abs(num):,.2f}"
        result = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
        return ('-' if negative else '') + result
    except (ValueError, TypeError):
        return value
