from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0005_transaction_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='reference_no',
            field=models.CharField(blank=True, max_length=60),
        ),
    ]
