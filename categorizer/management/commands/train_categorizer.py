from django.core.management.base import BaseCommand

from categorizer import classifier
from transactions.models import Transaction
from transactions.utils import DEFAULT_CATEGORIES


class Command(BaseCommand):
    help = 'Train the transaction categorizer (TF-IDF + Logistic Regression).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-user-data', action='store_true',
            help='Also learn from existing transactions (descriptions and category names only).',
        )

    def handle(self, *args, **options):
        import joblib
        from sklearn.metrics import classification_report
        from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split

        texts, labels = classifier.load_seed()
        self.stdout.write(f'Seed examples: {len(texts)}')

        if options['with_user_data']:
            allowed = set(DEFAULT_CATEGORIES) - {'Other'}
            rows = (Transaction.objects.exclude(description='')
                    .filter(category__name__in=allowed)
                    .values_list('description', 'category__name'))
            extra = list(rows)
            texts += [d for d, _ in extra]
            labels += [c for _, c in extra]
            self.stdout.write(f'Added from transactions: {len(extra)}')

        # 1) Honest test: train on 80%, test on the 20% the model has never seen
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=0.2, stratify=labels, random_state=42)
        model = classifier.build_pipeline().fit(X_train, y_train)
        predictions = model.predict(X_test)
        accuracy = (predictions == np_array(y_test)).mean()
        self.stdout.write(f'\nTest accuracy: {accuracy:.0%} on {len(y_test)} unseen examples')
        self.stdout.write(classification_report(y_test, predictions, zero_division=0))

        # 2) Cross-validation: repeat the test 5 times on different splits
        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        scores = cross_val_score(classifier.build_pipeline(), texts, labels, cv=cv)
        self.stdout.write(f'5-fold cross-validation: {scores.mean():.0%} (+/- {scores.std():.0%})')

        # 3) Final model uses all the data
        final = classifier.build_pipeline().fit(texts, labels)
        classifier.MODEL_PATH.parent.mkdir(exist_ok=True)
        joblib.dump(final, classifier.MODEL_PATH)
        self.stdout.write(self.style.SUCCESS(f'\nModel saved to {classifier.MODEL_PATH}'))


def np_array(values):
    import numpy as np
    return np.array(values)