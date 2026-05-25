import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0001_initial'),
        ('customers', '0002_customer_user'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerPayment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('payment_type', models.CharField(choices=[('nakit', 'Nakit'), ('havale', 'Havale'), ('eft', 'EFT'), ('cek', 'Çek'), ('kredi_karti', 'Kredi Kartı'), ('diger', 'Diğer')], max_length=20)),
                ('direction', models.CharField(choices=[('alindi', 'Alındı'), ('odendi', 'Ödendi')], max_length=10)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('date', models.DateField()),
                ('reference_no', models.CharField(blank=True, max_length=60)),
                ('description', models.TextField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='payment_entries', to='customers.customer')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='customer_payments', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
