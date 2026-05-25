from django.contrib import admin
from .models import Transaction

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'user', 'type', 'product', 'amount', 'date']
    list_filter = ['type', 'date', 'user']
    search_fields = ['customer__name', 'description']
    readonly_fields = ['amount', 'date', 'user']
    fieldsets = (
        ('İşlem Bilgileri', {
            'fields': ('user', 'customer', 'type', 'product', 'date')
        }),
        ('Tutar Detayları', {
            'fields': ('quantity', 'unit', 'unit_price', 'amount')
        }),
        ('Açıklama', {
            'fields': ('description',)
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:  # Yeni kayıt
            obj.user = request.user
        super().save_model(request, obj, form, change)
