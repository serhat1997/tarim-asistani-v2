import datetime
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0005_paymentplan_interest'),
        ('fields', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Expense',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('category', models.CharField(
                    choices=[
                        ('yevmiye', 'Yevmiye'),
                        ('yakıt', 'Yakıt'),
                        ('kira', 'Kira'),
                        ('elektrik', 'Elektrik'),
                        ('su', 'Su'),
                        ('dogalgaz', 'Doğalgaz'),
                        ('makine_bakim', 'Makine Bakım'),
                        ('nakliye', 'Nakliye'),
                        ('vergi_harc', 'Vergi / Harç'),
                        ('ofis', 'Ofis & Kırtasiye'),
                        ('diger', 'Diğer'),
                    ],
                    max_length=20,
                )),
                ('description', models.TextField(blank=True)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=12)),
                ('reference_no', models.CharField(blank=True, max_length=60)),
                ('field', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='genel_giderler',
                    to='fields.field',
                )),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='expenses',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={'ordering': ['-date', '-id']},
        ),
    ]
