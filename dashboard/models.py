from django.db import models
from django.contrib.auth.models import User
from customers.models import Customer
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver


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

    class Meta:
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['customer', 'direction']),
        ]

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
    total_amount   = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)   # anapara
    interest_rate  = models.DecimalField(max_digits=6, decimal_places=3, default=0)                # aylık % faiz
    amount = models.DecimalField(max_digits=12, decimal_places=2)                                  # taksit başı tutar
    due_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.get_payment_category_display()} - {self.customer.name} - {self.amount}"

    @property
    def paid_count(self):
        return self.taksitler.filter(is_paid=True).count()

    @property
    def overdue_count(self):
        from datetime import date
        return self.taksitler.filter(is_paid=False, due_date__lt=date.today()).count()


class Installment(models.Model):
    plan       = models.ForeignKey(PaymentPlan, on_delete=models.CASCADE, related_name='taksitler')
    number     = models.PositiveIntegerField()
    due_date   = models.DateField()
    amount     = models.DecimalField(max_digits=12, decimal_places=2)
    is_paid    = models.BooleanField(default=False)
    paid_date  = models.DateField(null=True, blank=True)
    reference_no = models.CharField(max_length=60, blank=True)
    note       = models.TextField(blank=True)

    class Meta:
        ordering = ['number']

    def __str__(self):
        return f"{self.plan} — Taksit {self.number}"

    @property
    def is_overdue(self):
        from datetime import date
        return not self.is_paid and self.due_date < date.today()


class Expense(models.Model):
    CATEGORIES = [
        ('yevmiye',      'Yevmiye'),
        ('yakıt',        'Yakıt'),
        ('kira',         'Kira'),
        ('elektrik',     'Elektrik'),
        ('su',           'Su'),
        ('dogalgaz',     'Doğalgaz'),
        ('makine_bakim', 'Makine Bakım'),
        ('nakliye',      'Nakliye'),
        ('vergi_harc',   'Vergi / Harç'),
        ('ofis',         'Ofis & Kırtasiye'),
        ('diger',        'Diğer'),
    ]

    user         = models.ForeignKey(User, on_delete=models.CASCADE, related_name='expenses')
    date         = models.DateField()
    category     = models.CharField(max_length=20, choices=CATEGORIES)
    description  = models.TextField(blank=True)
    amount       = models.DecimalField(max_digits=12, decimal_places=2)
    reference_no = models.CharField(max_length=60, blank=True)
    field        = models.ForeignKey('fields.Field', on_delete=models.SET_NULL,
                                     null=True, blank=True, related_name='genel_giderler')

    class Meta:
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['user', 'date']),
            models.Index(fields=['user', 'category']),
        ]

    def __str__(self):
        return f"{self.get_category_display()} — ₺{self.amount} ({self.date})"


class AuditLog(models.Model):
    ACTIONS = [('created', 'Oluşturuldu'), ('deleted', 'Silindi')]

    user        = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action      = models.CharField(max_length=10, choices=ACTIONS)
    model_name  = models.CharField(max_length=50)
    object_repr = models.CharField(max_length=255)
    timestamp   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M} | {self.model_name} {self.action} — {self.object_repr}"


# ─── Sinyal ile otomatik loglama ──────────────────────────────────────────────

def _log(action, instance, user=None):
    try:
        AuditLog.objects.create(
            user=user,
            action=action,
            model_name=instance.__class__.__name__,
            object_repr=str(instance)[:255],
        )
    except Exception:
        pass


@receiver(post_save)
def on_save(sender, instance, created, **kwargs):
    if sender.__name__ not in ('Transaction', 'CustomerPayment', 'Installment', 'Expense'):
        return
    if created:
        _log('created', instance)


@receiver(post_delete)
def on_delete(sender, instance, **kwargs):
    if sender.__name__ not in ('Transaction', 'CustomerPayment', 'Installment', 'PaymentPlan', 'Expense'):
        return
    _log('deleted', instance)
