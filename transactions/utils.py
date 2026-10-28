from .models import Category

DEFAULT_CATEGORIES = [
    'Food', 'Transportation', 'Education', 'Utilities',
    'Entertainment', 'Health', 'Shopping', 'Salary', 'Other',
]


def ensure_default_categories(user):
    """Give a user the starter categories if they have none yet."""
    if not user.categories.exists():
        Category.objects.bulk_create(
            [Category(user=user, name=name) for name in DEFAULT_CATEGORIES]
        )