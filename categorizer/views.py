from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from transactions.models import Category

from .classifier import predict_category


@login_required
def suggest(request):
    description = request.GET.get('description', '')
    tx_type = request.GET.get('type', 'expense')
    if tx_type not in ('income', 'expense'):
        tx_type = 'expense'

    result = predict_category(description, tx_type)
    if not result:
        return JsonResponse({'category_id': None})

    category = Category.objects.filter(user=request.user, name__iexact=result['label']).first()
    if not category:
        return JsonResponse({'category_id': None})
    return JsonResponse({
        'category_id': category.id,
        'category': category.name,
        'confidence': round(result['confidence'], 2),
    })