from django.urls import path
from . import views

urlpatterns = [
    path('',              views.inventory_list,   name='inventory_list'),
    path('ekle/',         views.inventory_create, name='inventory_create'),
    path('<int:pk>/duzenle/', views.inventory_edit,   name='inventory_edit'),
    path('<int:pk>/sil/', views.inventory_delete, name='inventory_delete'),
]
