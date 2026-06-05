from decimal import Decimal


def fmt_tr(value):
    """Ondalıklı sayıyı Türkçe biçimde döndürür: 1.234,56"""
    if value is None:
        return '—'
    try:
        num = Decimal(str(value))
    except Exception:
        return str(value)
    return f"{abs(num):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
