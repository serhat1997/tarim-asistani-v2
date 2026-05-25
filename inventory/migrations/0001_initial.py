from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='InventoryItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150, verbose_name='Envanter Adı')),
                ('category', models.CharField(
                    choices=[('arac','Araç & Ekipman'),('boru','Boru & Sulama'),('malzeme','Malzeme'),('elektronik','Elektronik'),('diger','Diğer')],
                    default='diger', max_length=20, verbose_name='Kategori'
                )),
                ('model_info', models.CharField(blank=True, max_length=150, verbose_name='Model / Marka')),
                ('quantity', models.DecimalField(decimal_places=2, default=1, max_digits=10, verbose_name='Adet / Miktar')),
                ('unit', models.CharField(
                    choices=[('adet','Adet'),('metre','Metre'),('kg','Kg'),('lt','Litre'),('paket','Paket'),('takim','Takım')],
                    default='adet', max_length=10, verbose_name='Birim'
                )),
                ('purchase_price', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Alış Tutarı (₺)')),
                ('purchase_date', models.DateField(verbose_name='Alınış Tarihi')),
                ('sale_price', models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name='Satış Tutarı (₺)')),
                ('sale_date', models.DateField(blank=True, null=True, verbose_name='Satış Tarihi')),
                ('notes', models.TextField(blank=True, verbose_name='Notlar')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='inventory_items',
                    to=settings.AUTH_USER_MODEL
                )),
            ],
            options={'ordering': ['-purchase_date', '-created_at']},
        ),
    ]
