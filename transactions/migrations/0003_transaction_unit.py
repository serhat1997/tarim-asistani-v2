from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0002_transaction_user'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='unit',
            field=models.CharField(choices=[('adet', 'Adet'), ('kg', 'Kg'), ('lt', 'Lt'), ('m', 'Metre'), ('paket', 'Paket')], default='adet', max_length=10),
            preserve_default=False,
        ),
    ]
