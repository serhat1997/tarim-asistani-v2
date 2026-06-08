from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('ekstre/', views.statement, name='statement'),
    path('ekstre/export/', views.statement_export, name='statement_export'),
    path('odemeler/', views.payments, name='payments'),
    path('odemeler/plan/ekle/', views.payment_create, name='payment_create'),
    path('odemeler/plan/<int:pk>/sil/', views.payment_plan_delete, name='payment_plan_delete'),
    path('odemeler/cari/ekle/', views.customer_payment_create, name='customer_payment_create'),
    path('odemeler/cari/<int:pk>/sil/', views.customer_payment_delete, name='customer_payment_delete'),
    path('odemeler/taksit/<int:pk>/ode/', views.installment_pay, name='installment_pay'),
    path('odemeler/taksit/<int:pk>/geri/', views.installment_unpay, name='installment_unpay'),
    path('musteriler/<int:pk>/bakiye-hesapla/', views.recalculate_balance, name='recalculate_balance'),
    path('giderler/', views.expense_list, name='expense_list'),
    path('giderler/ekle/', views.expense_create, name='expense_create'),
    path('giderler/<int:pk>/sil/', views.expense_delete, name='expense_delete'),
]
