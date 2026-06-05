from django.contrib import admin
from .models import PaymentPlan, CustomerPayment, AuditLog


@admin.register(PaymentPlan)
class PaymentPlanAdmin(admin.ModelAdmin):
    list_display  = ['id', 'customer', 'user', 'plan_type', 'payment_category', 'installments', 'amount', 'due_date', 'active', 'created_at']
    list_filter   = ['plan_type', 'payment_category', 'active', 'created_at']
    search_fields = ['customer__name', 'description']
    readonly_fields = ['created_at']


@admin.register(CustomerPayment)
class CustomerPaymentAdmin(admin.ModelAdmin):
    list_display  = ['id', 'customer', 'direction', 'payment_type', 'amount', 'date', 'user']
    list_filter   = ['direction', 'payment_type', 'date']
    search_fields = ['customer__name', 'reference_no', 'description']


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ['timestamp', 'user', 'action', 'model_name', 'object_repr']
    list_filter   = ['action', 'model_name', 'timestamp']
    search_fields = ['object_repr', 'user__username']
    readonly_fields = ['timestamp', 'user', 'action', 'model_name', 'object_repr']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
