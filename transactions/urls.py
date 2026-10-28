from django.urls import path
from . import views

urlpatterns = [
    path('', views.transaction_list, name='transaction_list'),
    path('add/', views.transaction_create, name='transaction_create'),
    path('upload/', views.upload_csv, name='upload_csv'),
    path('<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
]