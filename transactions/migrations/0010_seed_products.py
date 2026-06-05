from django.db import migrations

INITIAL_PRODUCTS = [
    # slug, name, product_type, default_unit, order
    ('cilek',   'Çilek',   'sale',     'kg',   1),
    ('elma',    'Elma',    'sale',     'kg',   2),
    ('kiraz',   'Kiraz',   'sale',     'kg',   3),
    ('seftali', 'Şeftali', 'sale',     'kg',   4),
    ('gubre',   'Gübre',   'purchase', 'kg',   10),
    ('fide',    'Fide',    'purchase', 'adet', 11),
    ('boru',    'Boru',    'purchase', 'm',    12),
    ('diger',   'Diğer',   'both',     'adet', 99),
]


def seed(apps, schema_editor):
    Product = apps.get_model('transactions', 'Product')
    for slug, name, ptype, unit, order in INITIAL_PRODUCTS:
        Product.objects.get_or_create(
            slug=slug,
            defaults=dict(name=name, product_type=ptype, default_unit=unit, order=order, active=True),
        )


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('transactions', '0009_product_model_dynamic'),
    ]
    operations = [
        migrations.RunPython(seed, unseed),
    ]
