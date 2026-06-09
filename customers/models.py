from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


class Customer(models.Model):
    CUSTOMER_TYPES = [
        ('hal',      'Hal'),
        ('pazarci',  'Pazarcı'),
        ('diger',    'Diğer'),
    ]

    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customers')
    name          = models.CharField(max_length=100)
    customer_type = models.CharField(max_length=10, choices=CUSTOMER_TYPES, default='diger', verbose_name='Cari Türü')
    tc_vkn        = models.CharField(max_length=20, blank=True, verbose_name='TC / VKN')
    address       = models.TextField(blank=True)
    phone         = models.CharField(max_length=20, blank=True)
    email         = models.EmailField(blank=True)
    balance       = models.DecimalField(max_digits=14, decimal_places=2, default=0)

    HAL_COMMISSION = Decimal('0.02')

    class Meta:
        indexes = [
            models.Index(fields=['user', 'name']),
            models.Index(fields=['user', 'customer_type']),
        ]

    def __str__(self):
        return self.name

    def recalculate_balance(self):
        """Tüm işlem ve ödemelerden bakiyeyi sıfırdan hesaplayıp kaydeder."""
        from django.db.models import Sum
        from transactions.models import Transaction
        from dashboard.models import CustomerPayment

        sales     = Transaction.objects.filter(customer=self, type='sale').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        purchases = Transaction.objects.filter(customer=self, type='purchase').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        received  = CustomerPayment.objects.filter(customer=self, direction='alindi').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        paid_out  = CustomerPayment.objects.filter(customer=self, direction='odendi').aggregate(s=Sum('amount'))['s'] or Decimal('0')
        self.balance = sales - purchases - received + paid_out
        self.save(update_fields=['balance'])
