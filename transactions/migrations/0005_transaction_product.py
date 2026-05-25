from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0004_alter_transaction_unit'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='product',
            field=models.CharField(choices=[('cilek', 'Çilek'), ('elma', 'Elma'), ('kiraz', 'Kiraz'), ('seftali', 'Şeftali'), ('gubre', 'Gübre'), ('fide', 'Fide'), ('boru', 'Boru')], default='cilek', max_length=20),
            preserve_default=False,
        ),
    ]
