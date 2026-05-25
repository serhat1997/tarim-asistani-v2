from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0002_inventoryitem_transaction_links'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventoryitem',
            name='sale_quantity',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, verbose_name='Satış Adedi'),
        ),
    ]
