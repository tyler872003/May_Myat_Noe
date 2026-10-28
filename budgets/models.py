from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models

from transactions.models import Category


class Budget(models.Model):
    """A monthly spending limit for one category."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='budgets')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='budgets')
    amount = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('1'))])

    class Meta:
        ordering = ['category__name']
        constraints = [
            models.UniqueConstraint(fields=['user', 'category'], name='unique_budget_per_category'),
        ]

    def __str__(self):
        return f'{self.category} - {self.amount}'