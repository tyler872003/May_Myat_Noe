from django.urls import path
from . import views

urlpatterns = [
    path('', views.budget_list, name='budget_list'),
    path('<int:pk>/delete/', views.budget_delete, name='budget_delete'),
]