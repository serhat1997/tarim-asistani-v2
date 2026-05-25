from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
        ('transactions', '0007_transaction_field_optional'),
    ]

    operations = [
        migrations.AddField(
            model_name='inventoryitem',
            name='source_transaction',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='inventory_purchase_item',
                to='transactions.transaction',
                verbose_name='Kaynak Alış İşlemi',
            ),
        ),
        migrations.AddField(
            model_name='inventoryitem',
            name='sale_transaction',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='inventory_sale_item',
                to='transactions.transaction',
                verbose_name='Bağlı Satış İşlemi',
            ),
        ),
    ]
