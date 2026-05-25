from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('ekstre/', views.statement, name='statement'),
    path('odemeler/', views.payments, name='payments'),
    path('odemeler/plan/ekle/', views.payment_create, name='payment_create'),
    path('odemeler/plan/<int:pk>/sil/', views.payment_plan_delete, name='payment_plan_delete'),
    path('odemeler/cari/ekle/', views.customer_payment_create, name='customer_payment_create'),
    path('odemeler/cari/<int:pk>/sil/', views.customer_payment_delete, name='customer_payment_delete'),
]