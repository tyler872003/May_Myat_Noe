import statistics
from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Min, Sum

from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from budgets.models import Budget
from transactions.models import Transaction

ZERO = Decimal('0')
WARNING_PERCENT = 90   # budget bar turns orange at 90%


def parse_month(value, today):
    """Turn '2026-10' into (2026, 10). Falls back to the current month."""
    try:
        year, month = (int(x) for x in value.split('-'))
        if not (1 <= month <= 12 and 2000 <= year <= 2100):
            raise ValueError
    except (AttributeError, ValueError):
        return today.year, today.month
    return year, month


def shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def month_transactions(user, year, month):
    return Transaction.objects.filter(user=user, date__year=year, date__month=month)


def monthly_summary(user, year, month):
    qs = month_transactions(user, year, month)
    income = qs.filter(type=Transaction.INCOME).aggregate(t=Sum('amount'))['t'] or ZERO
    expenses = qs.filter(type=Transaction.EXPENSE).aggregate(t=Sum('amount'))['t'] or ZERO
    savings = income - expenses
    rate = (savings / income * 100).quantize(Decimal('0.1')) if income > 0 else None
    return {'income': income, 'expenses': expenses, 'savings': savings, 'savings_rate': rate}


def category_breakdown(user, year, month):
    rows = (month_transactions(user, year, month)
            .filter(type=Transaction.EXPENSE)
            .values('category__name')
            .annotate(total=Sum('amount'))
            .order_by('-total'))
    return [{'name': r['category__name'] or 'Uncategorized', 'total': float(r['total'])} for r in rows]


def monthly_trend(user, year, month, months=6):
    start_y, start_m = shift_month(year, month, -(months - 1))
    end_y, end_m = shift_month(year, month, 1)
    rows = (Transaction.objects
            .filter(user=user, date__gte=date(start_y, start_m, 1), date__lt=date(end_y, end_m, 1))
            .annotate(m=TruncMonth('date'))
            .values('m', 'type')
            .annotate(total=Sum('amount')))
    totals = {(r['m'].year, r['m'].month, r['type']): float(r['total']) for r in rows}

    labels, income, expenses = [], [], []
    for i in range(months):
        y, m = shift_month(start_y, start_m, i)
        labels.append(f'{y}-{m:02d}')
        income.append(totals.get((y, m, Transaction.INCOME), 0))
        expenses.append(totals.get((y, m, Transaction.EXPENSE), 0))
    return {'labels': labels, 'income': income, 'expenses': expenses}


def budget_status(user, year, month):
    spent_rows = (month_transactions(user, year, month)
                  .filter(type=Transaction.EXPENSE)
                  .values('category_id')
                  .annotate(total=Sum('amount')))
    spent_by_cat = {r['category_id']: r['total'] for r in spent_rows}

    result = []
    for b in Budget.objects.filter(user=user).select_related('category'):
        spent = spent_by_cat.get(b.category_id, ZERO)
        percent = round(float(spent / b.amount * 100))
        if percent > 100:
            status = 'over'
        elif percent >= WARNING_PERCENT:
            status = 'warning'
        else:
            status = 'ok'
        result.append({
            'id': b.pk,
            'category': b.category.name,
            'budget': b.amount,
            'spent': spent,
            'remaining': b.amount - spent,
            'percent': percent,
            'bar': min(percent, 100),
            'status': status,
        })
    result.sort(key=lambda r: r['percent'], reverse=True)
    return result
# ---------------------------------------------------------------------------
# Week 5: forecast, budget alerts, unusual spending
# ---------------------------------------------------------------------------

def linear_forecast(values):
    """Least-squares line through the values; returns the next point."""
    n = len(values)
    mean_x = (n - 1) / 2
    mean_y = sum(values) / n
    denom = sum((x - mean_x) ** 2 for x in range(n))
    slope = sum((x - mean_x) * (y - mean_y) for x, y in enumerate(values)) / denom
    intercept = mean_y - slope * mean_x
    return max(intercept + slope * n, 0)


def expense_forecast(user, today, max_months=6, min_months=2):
    """Estimate this month's total expenses from the completed months before it."""
    first = Transaction.objects.filter(user=user, type=Transaction.EXPENSE).aggregate(d=Min('date'))['d']
    if first is None:
        return None

    months = []
    y, m = first.year, first.month
    while (y, m) < (today.year, today.month):
        months.append((y, m))
        y, m = shift_month(y, m, 1)
    months = months[-max_months:]

    if len(months) < min_months:
        return {'enough': False, 'months_needed': min_months, 'months_have': len(months)}

    rows = (Transaction.objects
            .filter(user=user, type=Transaction.EXPENSE,
                    date__gte=date(months[0][0], months[0][1], 1),
                    date__lt=date(today.year, today.month, 1))
            .annotate(m=TruncMonth('date'))
            .values('m')
            .annotate(total=Sum('amount')))
    totals = {(r['m'].year, r['m'].month): float(r['total']) for r in rows}
    values = [totals.get(ym, 0.0) for ym in months]

    average = sum(values) / len(values)
    if len(values) >= 3:
        predicted, method = linear_forecast(values), 'trend line'
    else:
        predicted, method = average, 'average'

    spent_so_far = (month_transactions(user, today.year, today.month)
                    .filter(type=Transaction.EXPENSE)
                    .aggregate(t=Sum('amount'))['t'] or ZERO)
    return {
        'enough': True,
        'predicted': round(predicted),
        'average': round(average),
        'method': method,
        'months_used': len(values),
        'spent_so_far': spent_so_far,
    }


def category_budget_alert(user, category, year, month):
    """A warning message if this category's budget is nearly used or exceeded."""
    for b in budget_status(user, year, month):
        if b['category'] == category.name and b['status'] != 'ok':
            if b['status'] == 'over':
                return (f"Budget alert: {b['category']} is over budget "
                        f"({b['percent']}% of {b['budget']:,.0f} MMK used).")
            return f"Budget alert: you have used {b['percent']}% of your {b['category']} budget."
    return None


def unusual_transactions(user, year, month, baseline_days=180, min_history=5):
    """Expenses far above the usual amount for their category.

    'Usual' = the median of that category's expenses in the 180 days before the
    month. The median and MAD (median absolute deviation) are used instead of the
    average, because one huge purchase would otherwise distort the average itself.
    """
    start = date(year, month, 1)
    end_y, end_m = shift_month(year, month, 1)
    end = date(end_y, end_m, 1)

    history = {}
    past_rows = (Transaction.objects
                 .filter(user=user, type=Transaction.EXPENSE, category__isnull=False,
                         date__gte=start - timedelta(days=baseline_days), date__lt=start)
                 .values_list('category_id', 'amount'))
    for cat_id, amount in past_rows:
        history.setdefault(cat_id, []).append(float(amount))

    current = (Transaction.objects
               .filter(user=user, type=Transaction.EXPENSE, category__isnull=False,
                       date__gte=start, date__lt=end)
               .select_related('category'))

    flagged = []
    for t in current:
        past = history.get(t.category_id, [])
        if len(past) < min_history:
            continue
        median = statistics.median(past)
        mad = statistics.median([abs(x - median) for x in past])
        spread = 1.4826 * max(mad, 0.1 * median)
        threshold = median + 3.5 * spread
        amount = float(t.amount)
        if amount > threshold and amount >= 1.5 * median:
            flagged.append({
                'id': t.pk,
                'date': t.date,
                'category': t.category.name,
                'description': t.description,
                'amount': t.amount,
                'typical': round(median),
                'times': round(amount / median, 1),
            })
    return flagged