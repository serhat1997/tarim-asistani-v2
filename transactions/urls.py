from django.urls import path
from . import views

urlpatterns = [
    path('create/',                      views.transaction_create, name='transaction_create'),
    path('<int:pk>/sil/',                views.transaction_delete, name='transaction_delete'),
    path('urunler/',                     views.product_list,       name='product_list'),
    path('urunler/ekle/',                views.product_create,     name='product_create'),
    path('urunler/<int:pk>/toggle/',     views.product_toggle,     name='product_toggle'),
    path('urunler/<int:pk>/sil/',        views.product_delete,     name='product_delete'),
]
