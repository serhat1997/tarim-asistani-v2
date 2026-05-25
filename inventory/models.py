from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal


CATEGORIES = [
    ('arac',     'Araç & Ekipman'),
    ('boru',     'Boru & Sulama'),
    ('malzeme',  'Malzeme'),
    ('elektronik','Elektronik'),
    ('diger',    'Diğer'),
]

UNITS = [
    ('adet',  'Adet'),
    ('metre', 'Metre'),
    ('kg',    'Kg'),
    ('lt',    'Litre'),
    ('paket', 'Paket'),
    ('takim', 'Takım'),
]


class InventoryItem(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='inventory_items')
    name          = models.CharField(max_length=150, verbose_name='Envanter Adı')
    category      = models.CharField(max_length=20, choices=CATEGORIES, default='diger', verbose_name='Kategori')
    model_info    = models.CharField(max_length=150, blank=True, verbose_name='Model / Marka')
    quantity      = models.DecimalField(max_digits=10, decimal_places=2, default=1, verbose_name='Adet / Miktar')
    unit          = models.CharField(max_length=10, choices=UNITS, default='adet', verbose_name='Birim')
    purchase_price = models.DecimalField(max_digits=14, decimal_places=2, verbose_name='Alış Tutarı (₺)')
    purchase_date  = models.DateField(verbose_name='Alınış Tarihi')
    sale_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name='Satış Adedi')
    sale_price    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True, verbose_name='Satış Tutarı (₺)')
    sale_date     = models.DateField(null=True, blank=True, verbose_name='Satış Tarihi')
    notes         = models.TextField(blank=True, verbose_name='Notlar')
    source_transaction = models.ForeignKey(
        'transactions.Transaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='inventory_purchase_item',
        verbose_name='Kaynak Alış İşlemi'
    )
    sale_transaction = models.ForeignKey(
        'transactions.Transaction',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='inventory_sale_item',
        verbose_name='Bağlı Satış İşlemi'
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-purchase_date', '-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_category_display()})"

    @property
    def is_sold(self):
        return self.sale_date is not None

    @property
    def is_partial_sale(self):
        return (self.sale_date is not None and
                self.sale_quantity is not None and
                self.sale_quantity < self.quantity)

    @property
    def remaining_quantity(self):
        if self.sale_quantity is not None:
            return self.quantity - self.sale_quantity
        if self.sale_date:
            return Decimal('0')
        return self.quantity

    def _effective_purchase_cost(self):
        """Satılan adet için orantılı alış maliyeti."""
        sold_qty = self.sale_quantity if self.sale_quantity is not None else self.quantity
        if self.quantity:
            return (self.purchase_price / self.quantity) * sold_qty
        return self.purchase_price

    @property
    def profit(self):
        if self.sale_price is not None:
            return self.sale_price - self._effective_purchase_cost()
        return None

    @property
    def profit_pct(self):
        if self.sale_price is not None:
            cost = self._effective_purchase_cost()
            if cost:
                return ((self.sale_price - cost) / cost) * 100
        return None

    @property
    def unit_purchase_price(self):
        if self.quantity:
            return self.purchase_price / self.quantity
        return self.purchase_price

    @property
    def unit_sale_price(self):
        sold_qty = self.sale_quantity if self.sale_quantity is not None else self.quantity
        if self.sale_price is not None and sold_qty:
            return self.sale_price / sold_qty
        return None
