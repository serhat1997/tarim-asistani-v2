from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('fields', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='LandTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('transaction_type', models.CharField(choices=[('alis', 'Alış'), ('satis', 'Satış')], max_length=5)),
                ('date', models.DateField()),
                ('area_decare', models.DecimalField(decimal_places=2, max_digits=8, verbose_name='Dönüm')),
                ('price_per_decare', models.DecimalField(decimal_places=2, max_digits=14, verbose_name='Dönüm Fiyatı (₺)')),
                ('additional_costs', models.DecimalField(decimal_places=2, default=0, help_text='Tapu harcı, komisyon, vergi vb.', max_digits=12, verbose_name='Ek Masraflar (₺)')),
                ('counterparty', models.CharField(blank=True, max_length=120, verbose_name='Satıcı / Alıcı')),
                ('deed_no', models.CharField(blank=True, max_length=60, verbose_name='Tapu / Sözleşme No')),
                ('notes', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('field', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='land_transactions', to='fields.field')),
            ],
            options={
                'ordering': ['date'],
            },
        ),
    ]
