from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth

from transactions.models import Transaction   # <- change to your app/model


def _month_range(month: str):
    y, m = map(int, month.split('-'))
    start = date(y, m, 1)
    end = date(y + (m == 12), (m % 12) + 1, 1)
    return start, end


def _num(x):
    return int(x or Decimal(0))


def make_tools(user, today):
    """Tools are bound to ONE user. The model can never choose whose data to read."""

    def get_month_summary(month: str) -> dict:
        """Total income, total expense and net saving for one month. month format: 'YYYY-MM' (e.g. '2026-03')."""
        try:
            start, end = _month_range(month)
        except Exception:
            return {'error': 'month must be YYYY-MM'}
        qs = Transaction.objects.filter(user=user, date__gte=start, date__lt=end)
        income = _num(qs.filter(type='income').aggregate(s=Sum('amount'))['s'])
        expense = _num(qs.filter(type='expense').aggregate(s=Sum('amount'))['s'])
        return {'month': month, 'income': income, 'expense': expense,
                'net_saving': income - expense, 'has_data': qs.exists()}

    def get_category_totals(month: str, kind: str = 'expense') -> list:
        """Totals per category for one month, sorted from highest to lowest.
        month format 'YYYY-MM'. kind is 'expense' or 'income'.
        The first item is the highest category and the last item is the lowest."""
        try:
            start, end = _month_range(month)
        except Exception:
            return [{'error': 'month must be YYYY-MM'}]
        rows = (Transaction.objects
                .filter(user=user, type=kind, date__gte=start, date__lt=end)
                .values('category').annotate(total=Sum('amount')).order_by('-total'))
        return [{'category': str(r['category']), 'total': _num(r['total'])} for r in rows]

    def get_recent_months(count: int = 6) -> list:
        """Income, expense and net saving for each of the last N months (max 12), oldest first. Use for trends, averages and 'why did spending go up'."""
        count = max(1, min(count, 12))
        rows = (Transaction.objects.filter(user=user)
                .annotate(m=TruncMonth('date')).values('m', 'type')
                .annotate(total=Sum('amount')).order_by('m'))
        data = {}
        for r in rows:
            key = r['m'].strftime('%Y-%m')
            data.setdefault(key, {'month': key, 'income': 0, 'expense': 0})
            data[key][r['type']] = _num(r['total'])
        out = list(data.values())[-count:]
        for d in out:
            d['net_saving'] = d['income'] - d['expense']
        return out

    def get_largest_expenses(month: str, limit: int = 5) -> list:
        """The biggest individual expenses in one month ('YYYY-MM'). Use to find unusual spending."""
        try:
            start, end = _month_range(month)
        except Exception:
            return [{'error': 'month must be YYYY-MM'}]
        qs = (Transaction.objects.filter(user=user, type='expense', date__gte=start, date__lt=end)
              .order_by('-amount')[:max(1, min(limit, 10))])
        return [{'date': t.date.isoformat(), 'category': str(t.category), 'amount': _num(t.amount)} for t in qs]

    def savings_plan(target_amount: int, months: int) -> dict:
        """Check a savings goal. Example: 10,000,000 in 12 months. Returns the required saving per month
        and compares it with the user's average monthly net saving over recent months."""
        months = max(1, months)
        required = round(target_amount / months)
        recent = get_recent_months(3)
        avg = round(sum(r['net_saving'] for r in recent) / len(recent)) if recent else 0
        return {'target': target_amount, 'months': months, 'required_per_month': required,
                'average_monthly_net_saving_recent': avg, 'gap_per_month': required - avg}

    return [get_month_summary, get_category_totals, get_recent_months,
            get_largest_expenses, savings_plan]