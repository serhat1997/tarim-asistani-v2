from django.urls import path
from . import views

urlpatterns = [
    path('', views.field_list, name='field_list'),
    path('ekle/', views.field_create, name='field_create'),
    path('<int:pk>/', views.field_detail, name='field_detail'),
    path('<int:pk>/duzenle/', views.field_edit, name='field_edit'),
    path('<int:pk>/sil/', views.field_delete, name='field_delete'),
    path('<int:pk>/hasat/ekle/', views.harvest_add, name='harvest_add'),
    path('<int:pk>/hasat/<int:hpk>/sil/', views.harvest_delete, name='harvest_delete'),
    path('<int:pk>/gider/ekle/', views.expense_add, name='expense_add'),
    path('<int:pk>/gider/<int:epk>/sil/', views.expense_delete, name='expense_delete'),
    path('<int:pk>/arazi/ekle/', views.land_transaction_add, name='land_transaction_add'),
    path('<int:pk>/arazi/<int:lpk>/sil/', views.land_transaction_delete, name='land_transaction_delete'),
]
