from decimal import Decimal

from django import forms

from transactions.models import Category


class BudgetForm(forms.Form):
    category = forms.ModelChoiceField(queryset=Category.objects.none())
    amount = forms.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('1'),
                                label='Monthly limit (MMK)')

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(user=user)