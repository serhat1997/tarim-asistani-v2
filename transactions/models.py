from django.db import models
from django.contrib.auth.models import User
from customers.models import Customer
from fields.models import Field

class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('purchase', 'Alış'),
        ('sale', 'Satış'),
    ]
    SALE_PRODUCTS = [
        ('cilek', 'Çilek'),
        ('elma', 'Elma'),
        ('kiraz', 'Kiraz'),
        ('seftali', 'Şeftali'),
        ('diger', 'Diğer'),
    ]
    PURCHASE_PRODUCTS = [
        ('gubre', 'Gübre'),
        ('fide', 'Fide'),
        ('boru', 'Boru'),
        ('diger', 'Diğer'),
    ]
    UNIT_CHOICES = [
        ('adet', 'Adet'),
        ('kg', 'Kg'),
        ('lt', 'Lt'),
        ('m', 'Metre'),
        ('paket', 'Paket'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    field = models.ForeignKey(Field, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions', verbose_name='Tarla')
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    product = models.CharField(max_length=20, choices=SALE_PRODUCTS + PURCHASE_PRODUCTS)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default='adet')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    date = models.DateField(auto_now_add=True)
    reference_no = models.CharField(max_length=60, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.customer.name} - {self.type} - {self.quantity} {self.unit} - {self.amount}"

    def save(self, *args, **kwargs):
        # Calculate amount from quantity and unit_price
        self.amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # Update customer balance
        if self.type == 'sale':
            self.customer.balance += self.amount
        elif self.type == 'purchase':
            self.customer.balance -= self.amount
        self.customer.save()
