from django.urls import path
from . import views

urlpatterns = [
    path('create/', views.transaction_create, name='transaction_create'),
    path('<int:pk>/sil/', views.transaction_delete, name='transaction_delete'),
]