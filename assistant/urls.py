from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat, name='assistant_chat'),
    path('ask/', views.ask, name='assistant_ask'),
    path('clear/', views.clear, name='assistant_clear'),
]