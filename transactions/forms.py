from django import forms

from config.bootstrap_forms import BootstrapFormMixin

from .models import Category, Transaction


class TransactionForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['type', 'amount', 'category', 'description', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show this user's own categories
        self.fields['category'].queryset = Category.objects.filter(user=user)


class CSVUploadForm(BootstrapFormMixin, forms.Form):
    file = forms.FileField(label='CSV file')