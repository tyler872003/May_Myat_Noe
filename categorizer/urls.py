from django.urls import path
from . import views

urlpatterns = [
    path('suggest/', views.suggest, name='category_suggest'),
]