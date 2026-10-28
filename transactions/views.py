import csv
import io
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction as db_transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from dashboard.analytics import category_budget_alert
from categorizer.classifier import predict_category

from .forms import CSVUploadForm, TransactionForm
from .models import Category, Transaction
from .utils import ensure_default_categories

MAX_CSV_SIZE = 2 * 1024 * 1024  # 2 MB


@login_required
def transaction_list(request):
    ensure_default_categories(request.user)
    qs = Transaction.objects.filter(user=request.user).select_related('category')
    page = Paginator(qs, 25).get_page(request.GET.get('page'))
    return render(request, 'transactions/list.html', {'page': page})


@login_required
def transaction_create(request):
    ensure_default_categories(request.user)
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user
            obj.save()
            messages.success(request, 'Transaction added.')
            if obj.type == Transaction.EXPENSE and obj.category:
                alert = category_budget_alert(request.user, obj.category, obj.date.year, obj.date.month)
                if alert:
                    messages.warning(request, alert)
            return redirect('transaction_list')
    else:
        form = TransactionForm(user=request.user, initial={'date': date.today()})
    return render(request, 'transactions/form.html', {'form': form})

@login_required
@require_POST
def transaction_delete(request, pk):
    obj = get_object_or_404(Transaction, pk=pk, user=request.user)
    obj.delete()
    messages.success(request, 'Transaction deleted.')
    return redirect('transaction_list')


@login_required
def upload_csv(request):
    if request.method == 'POST':
        form = CSVUploadForm(request.POST, request.FILES)
        if form.is_valid():
            f = form.cleaned_data['file']
            if f.size > MAX_CSV_SIZE:
                messages.error(request, 'File is too large (max 2 MB).')
                return redirect('upload_csv')
            try:
                text = f.read().decode('utf-8-sig')
            except UnicodeDecodeError:
                messages.error(request, 'File must be a UTF-8 encoded CSV.')
                return redirect('upload_csv')

            reader = csv.DictReader(io.StringIO(text))
            reader.fieldnames = [h.strip().lower() for h in (reader.fieldnames or [])]
            if not {'date', 'type', 'amount'}.issubset(reader.fieldnames):
                messages.error(request, 'CSV must have the columns: date, type, amount (category and description are optional).')
                return redirect('upload_csv')

            parsed, errors = [], []
            for line_no, row in enumerate(reader, start=2):
                try:
                    d = datetime.strptime((row.get('date') or '').strip(), '%Y-%m-%d').date()
                    t = (row.get('type') or '').strip().lower()
                    if t not in ('income', 'expense'):
                        raise ValueError('type must be income or expense')
                    amount = Decimal((row.get('amount') or '').replace(',', '').strip())
                    if amount <= 0:
                        raise ValueError('amount must be positive')
                    desc = (row.get('description') or '').strip()[:255]

                    raw_cat = (row.get('category') or '').strip()
                    auto = False
                    if raw_cat:
                        cat_name = raw_cat[:50]
                    else:
                        guess = predict_category(desc, t)
                        cat_name = guess['label'] if guess else 'Other'
                        auto = guess is not None
                    parsed.append((d, t, amount, cat_name, desc, auto))
                except (ValueError, InvalidOperation) as e:
                    errors.append(f'Line {line_no}: {e}')

            if errors:
                shown = '; '.join(errors[:5])
                more = f' (+{len(errors) - 5} more)' if len(errors) > 5 else ''
                messages.error(request, f'Nothing was imported. {shown}{more}')
                return redirect('upload_csv')
            if not parsed:
                messages.error(request, 'The file has no data rows.')
                return redirect('upload_csv')

            with db_transaction.atomic():
                cats = {c.name.lower(): c for c in Category.objects.filter(user=request.user)}
                to_create = []
                for d, t, amount, cat_name, desc, _auto in parsed:
                    cat = cats.get(cat_name.lower())
                    if cat is None:
                        cat = Category.objects.create(user=request.user, name=cat_name)
                        cats[cat_name.lower()] = cat
                    to_create.append(Transaction(user=request.user, date=d, type=t,
                                                 amount=amount, category=cat, description=desc))
                Transaction.objects.bulk_create(to_create)

            auto_count = sum(1 for p in parsed if p[5])
            messages.success(request, f'Imported {len(to_create)} transactions ({auto_count} categorized automatically).')
            return redirect('transaction_list')
    else:
        form = CSVUploadForm()
    return render(request, 'transactions/upload.html', {'form': form})