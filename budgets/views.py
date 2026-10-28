from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from dashboard.analytics import budget_status
from transactions.utils import ensure_default_categories

from .forms import BudgetForm
from .models import Budget


@login_required
def budget_list(request):
    ensure_default_categories(request.user)
    if request.method == 'POST':
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            Budget.objects.update_or_create(
                user=request.user,
                category=form.cleaned_data['category'],
                defaults={'amount': form.cleaned_data['amount']},
            )
            messages.success(request, 'Budget saved.')
            return redirect('budget_list')
    else:
        form = BudgetForm(user=request.user)

    today = timezone.localdate()
    return render(request, 'budgets/list.html', {
        'form': form,
        'budgets': budget_status(request.user, today.year, today.month),
        'month_label': today.strftime('%B %Y'),
    })


@login_required
@require_POST
def budget_delete(request, pk):
    get_object_or_404(Budget, pk=pk, user=request.user).delete()
    messages.success(request, 'Budget deleted.')
    return redirect('budget_list')