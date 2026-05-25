from django.db import models
from django.contrib.auth.models import User
from customers.models import Customer


class CustomerPayment(models.Model):
    PAYMENT_TYPES = [
        ('nakit', 'Nakit'),
        ('havale', 'Havale'),
        ('eft', 'EFT'),
        ('cek', 'Çek'),
        ('kredi_karti', 'Kredi Kartı'),
        ('diger', 'Diğer'),
    ]
    DIRECTIONS = [
        ('alindi', 'Alındı'),
        ('odendi', 'Ödendi'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_payments')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payment_entries')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES)
    direction = models.CharField(max_length=10, choices=DIRECTIONS)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField()
    reference_no = models.CharField(max_length=60, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.name} - {self.get_direction_display()} - {self.get_payment_type_display()} - {self.amount}"


class PaymentPlan(models.Model):
    PLAN_TYPES = [
        ('monthly', 'Aylık'),
        ('yearly', 'Yıllık'),
    ]
    PAYMENT_CATEGORIES = [
        ('tarla_kira', 'Tarla Kira'),
        ('kredi', 'Kredi'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_plans')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='payment_plans')
    plan_type = models.CharField(max_length=10, choices=PLAN_TYPES)
    payment_category = models.CharField(max_length=20, choices=PAYMENT_CATEGORIES)
    installments = models.PositiveIntegerField(default=1)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_payment_category_display()} - {self.customer.name} - {self.amount}"
