from django.contrib import admin
from django.urls import path, include

from accounts.views import welcome

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', welcome, name='welcome'),
    path('dashboard/', include('dashboard.urls')),
    path('accounts/', include('accounts.urls')),
    path('transactions/', include('transactions.urls')),
    path('budgets/', include('budgets.urls')),
    path('categorizer/', include('categorizer.urls')),
    path('assistant/', include('assistant.urls')),
]