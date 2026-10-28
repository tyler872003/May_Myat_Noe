import calendar
from datetime import date

from dashboard.analytics import (budget_status, category_breakdown, expense_forecast,
                                 monthly_summary, monthly_trend, shift_month,
                                 unusual_transactions)
from transactions.models import Transaction


def _summary(user, year, month):
    s = monthly_summary(user, year, month)
    return {
        'income': float(s['income']),
        'expenses': float(s['expenses']),
        'savings': float(s['savings']),
        'savings_rate_percent': float(s['savings_rate']) if s['savings_rate'] is not None else None,
    }


def build_facts(user, today):
    """Everything the assistant may talk about, all calculated by the backend."""
    year, month = today.year, today.month
    prev_year, prev_month = shift_month(year, month, -1)

    this_cats = category_breakdown(user, year, month)
    last_cats = category_breakdown(user, prev_year, prev_month)
    now_by = {c['name']: c['total'] for c in this_cats}
    before_by = {c['name']: c['total'] for c in last_cats}
    changes = [
        {
            'category': name,
            'this_month': now_by.get(name, 0.0),
            'last_month': before_by.get(name, 0.0),
            'change': round(now_by.get(name, 0.0) - before_by.get(name, 0.0), 2),
        }
        for name in set(now_by) | set(before_by)
    ]
    changes.sort(key=lambda c: abs(c['change']), reverse=True)

    largest = (Transaction.objects
               .filter(user=user, type=Transaction.EXPENSE, date__year=year, date__month=month)
               .select_related('category')
               .order_by('-amount')[:5])

    forecast = expense_forecast(user, today)
    forecast_facts = None
    if forecast and forecast['enough']:
        forecast_facts = {
            'expected_total_for_this_month': forecast['predicted'],
            'spent_so_far': float(forecast['spent_so_far']),
            'method': forecast['method'],
            'completed_months_used': forecast['months_used'],
        }

    return {
        'currency': 'MMK',
        'today': today.isoformat(),
        'this_month_progress': {
            'day_of_month': today.day,
            'days_in_month': calendar.monthrange(year, month)[1],
        },
        'this_month': {
            'label': date(year, month, 1).strftime('%B %Y'),
            'summary': _summary(user, year, month),
            'spending_by_category': this_cats,
            'budgets': [
                {'category': b['category'], 'budget': float(b['budget']),
                 'spent': float(b['spent']), 'percent_used': b['percent'], 'status': b['status']}
                for b in budget_status(user, year, month)
            ],
            'largest_expenses': [
                {'date': t.date.isoformat(), 'amount': float(t.amount),
                 'category': t.category.name if t.category else 'Uncategorized',
                 'description': t.description}
                for t in largest
            ],
            'unusual_spending': [
                {'date': u['date'].isoformat(), 'category': u['category'], 'amount': float(u['amount']),
                 'typical_amount_for_category': u['typical'], 'times_typical': u['times']}
                for u in unusual_transactions(user, year, month)
            ],
        },
        'last_month': {
            'label': date(prev_year, prev_month, 1).strftime('%B %Y'),
            'summary': _summary(user, prev_year, prev_month),
            'spending_by_category': last_cats,
        },
        'category_change_vs_last_month': changes,
        'expected_spending_this_month': forecast_facts,
        'last_6_months': monthly_trend(user, year, month),
    }