from django.contrib import admin
from .models import Customer

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'phone', 'email', 'balance']
    list_filter = ['user', 'email']
    search_fields = ['name', 'phone', 'email']
    readonly_fields = ['balance']
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('user', 'name', 'email', 'phone')
        }),
        ('Adres ve Detaylar', {
            'fields': ('address', 'balance')
        }),
    )
