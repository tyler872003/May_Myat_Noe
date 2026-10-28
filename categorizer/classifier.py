import csv
from pathlib import Path

import joblib
import numpy as np

BASE = Path(__file__).resolve().parent
SEED_CSV = BASE / 'data' / 'seed_expenses.csv'
MODEL_PATH = BASE / 'models' / 'categorizer.joblib'

CONFIDENCE_THRESHOLD = 0.40   # below this, we don't guess
INCOME_LABELS = {'Salary'}    # labels allowed for income; everything else is for expenses

_model = None


def build_pipeline():
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import Pipeline

    return Pipeline([
        ('tfidf', TfidfVectorizer(analyzer='char_wb', ngram_range=(2, 5),
                                  lowercase=True, sublinear_tf=True)),
        ('clf', LogisticRegression(max_iter=1000, C=10, class_weight='balanced')),
    ])


def load_seed():
    texts, labels = [], []
    with open(SEED_CSV, encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            texts.append(row['description'].strip())
            labels.append(row['category'].strip())
    return texts, labels


def load_model():
    global _model
    if _model is None and MODEL_PATH.exists():
        _model = joblib.load(MODEL_PATH)
    return _model


def predict_category(description, transaction_type):
    """Return {'label': ..., 'confidence': ...} or None if unsure / no model."""
    description = (description or '').strip()
    model = load_model()
    if not description or model is None:
        return None

    probs = model.predict_proba([description])[0]
    classes = model.classes_
    is_income = transaction_type == 'income'
    allowed = np.array([(c in INCOME_LABELS) == is_income for c in classes])
    masked = np.where(allowed, probs, 0.0)

    best = int(masked.argmax())
    confidence = float(masked[best])
    if confidence < CONFIDENCE_THRESHOLD:
        return None
    return {'label': str(classes[best]), 'confidence': confidence}