from django.contrib import admin
from .models import PaymentPlan


@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'user', 'plan_type', 'payment_category', 'installments', 'amount', 'due_date', 'active', 'created_at']
    list_filter = ['plan_type', 'payment_category', 'active', 'created_at']
    search_fields = ['customer__name', 'description']
    readonly_fields = ['created_at']
