from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from .analytics import (budget_status, category_breakdown, expense_forecast,
                        monthly_summary, monthly_trend, parse_month, shift_month,
                        unusual_transactions)


@login_required
def dashboard(request):
    today = timezone.localdate()
    year, month = parse_month(request.GET.get('month'), today)
    prev_y, prev_m = shift_month(year, month, -1)
    next_y, next_m = shift_month(year, month, 1)
    is_current = (year, month) == (today.year, today.month)

    budgets = budget_status(request.user, year, month)

    context = {
        'summary': monthly_summary(request.user, year, month),
        'budgets': budgets,
        'alerts': [b for b in budgets if b['status'] != 'ok'] if is_current else [],
        'forecast': expense_forecast(request.user, today) if is_current else None,
        'unusual': unusual_transactions(request.user, year, month),
        'charts': {
            'categories': category_breakdown(request.user, year, month),
            'trend': monthly_trend(request.user, year, month),
        },
        'month_label': date(year, month, 1).strftime('%B %Y'),
        'prev_month': f'{prev_y}-{prev_m:02d}',
        'next_month': f'{next_y}-{next_m:02d}',
        'is_current': is_current,
    }
    return render(request, 'dashboard/dashboard.html', context)