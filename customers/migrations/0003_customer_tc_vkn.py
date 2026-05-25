from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customers', '0002_customer_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='tc_vkn',
            field=models.CharField(blank=True, max_length=20, verbose_name='TC / VKN'),
        ),
    ]
