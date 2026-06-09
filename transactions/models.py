from django.db import models, transaction as db_transaction
from django.contrib.auth.models import User
from customers.models import Customer
from fields.models import Field
import datetime


class Product(models.Model):
    PRODUCT_TYPES = [
        ('sale', 'Satış'),
        ('purchase', 'Alış'),
        ('both', 'Her İkisi'),
    ]
    UNIT_CHOICES = [
        ('adet', 'Adet'),
        ('kg', 'Kg'),
        ('lt', 'Lt'),
        ('m', 'Metre'),
        ('paket', 'Paket'),
    ]

    slug = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    product_type = models.CharField(max_length=10, choices=PRODUCT_TYPES)
    default_unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='kg')
    active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Alış'),
        ('sale', 'Satış'),
    ]
    # Geriye dönük uyumluluk için sabit listeler korunuyor
    SALE_PRODUCTS = [
        ('cilek', 'Çilek'), ('elma', 'Elma'), ('kiraz', 'Kiraz'),
        ('seftali', 'Şeftali'), ('diger', 'Diğer'),
    ]
    PURCHASE_PRODUCTS = [
        ('gubre', 'Gübre'), ('fide', 'Fide'), ('boru', 'Boru'), ('diger', 'Diğer'),
    ]
    UNIT_CHOICES = [
        ('adet', 'Adet'), ('kg', 'Kg'), ('lt', 'Lt'), ('m', 'Metre'), ('paket', 'Paket'),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    customer   = models.ForeignKey(Customer, on_delete=models.CASCADE)
    field      = models.ForeignKey(Field, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='transactions', verbose_name='Tarla')
    type       = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    product    = models.CharField(max_length=100)   # slug — eski kayıtlarla uyumlu
    quantity   = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit       = models.CharField(max_length=10, choices=UNIT_CHOICES, default='adet')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount     = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    date       = models.DateField(default=datetime.date.today)
    reference_no = models.CharField(max_length=60, blank=True)
    description  = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'type']),
            models.Index(fields=['customer', 'date']),
            models.Index(fields=['customer', 'type']),
        ]

    def __str__(self):
        return f"{self.customer.name} - {self.type} - {self.quantity} {self.unit} - {self.amount}"

    def get_product_display(self):
        try:
            return Product.objects.get(slug=self.product).name
        except Product.DoesNotExist:
            # Eski kayıtlar için sabit listeden ara
            mapping = dict(self.SALE_PRODUCTS + self.PURCHASE_PRODUCTS)
            return mapping.get(self.product, self.product)

    def get_unit_display(self):
        return dict(self.UNIT_CHOICES).get(self.unit, self.unit)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        gross = self.quantity * self.unit_price
        # Hal müşterisine satışta %2 komisyon kesintisi uygulanır
        if self.type == 'sale' and self.customer.customer_type == 'hal':
            from decimal import Decimal
            self.amount = (gross * (Decimal('1') - Customer.HAL_COMMISSION)).quantize(Decimal('0.01'))
        else:
            self.amount = gross
        with db_transaction.atomic():
            super().save(*args, **kwargs)
            if is_new:
                if self.type == 'sale':
                    Customer.objects.filter(pk=self.customer_id).update(
                        balance=models.F('balance') + self.amount)
                elif self.type == 'purchase':
                    Customer.objects.filter(pk=self.customer_id).update(
                        balance=models.F('balance') - self.amount)

    def delete(self, *args, **kwargs):
        with db_transaction.atomic():
            if self.type == 'sale':
                Customer.objects.filter(pk=self.customer_id).update(
                    balance=models.F('balance') - self.amount)
            elif self.type == 'purchase':
                Customer.objects.filter(pk=self.customer_id).update(
                    balance=models.F('balance') + self.amount)
            super().delete(*args, **kwargs)
