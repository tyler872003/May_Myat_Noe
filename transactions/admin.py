from django.contrib import admin
from .models import Category, Transaction

admin.site.register(Category)

@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('date', 'user', 'type', 'amount', 'category')
    list_filter = ('type', 'category')