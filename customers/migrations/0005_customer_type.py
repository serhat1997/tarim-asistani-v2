from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0004_balance_precision'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='customer_type',
            field=models.CharField(
                choices=[('hal', 'Hal'), ('pazarci', 'Pazarcı'), ('diger', 'Diğer')],
                default='diger',
                max_length=10,
                verbose_name='Cari Türü',
            ),
        ),
    ]
