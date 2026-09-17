import hashlib
import os

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

from . import config

_WORKSPACE = None

# Demo training data: clearly synthetic and intended only to make the prototype
# runnable without patient data. Not for real clinical decisions.


def synthetic_data(n=None, seed=None):
    n = n or config.SYNTHETIC['n']
    seed = seed if seed is not None else config.SYNTHETIC['seed']
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        age = int(rng.integers(18, 81))
        sex = rng.choice(['Male', 'Female'])
        smoking = rng.choice(['Yes', 'No'], p=[.28, .72])
        diabetes = rng.choice(['Yes', 'No'], p=[.18, .82])
        pain = rng.choice(['Yes', 'No'], p=[.42, .58])
        bleed = rng.choice(['Yes', 'No'], p=[.38, .62])
        caries = int(rng.poisson(2.5))
        missing = int(min(rng.poisson(max(age - 35, 1) / 14), 15))
        hygiene = rng.choice(['Good', 'Fair', 'Poor'], p=[.35, .45, .20])
        perio = rng.choice(['Healthy', 'Mild', 'Moderate', 'Severe'], p=[.35, .30, .25, .10])
        score = 0.0
        score += 1.4 if pain == 'Yes' else 0
        score += 0.8 if bleed == 'Yes' else 0
        score += 0.35 * caries + 0.22 * missing
        score += {'Good': 0, 'Fair': .5, 'Poor': 1.1}[hygiene]
        score += {'Healthy': 0, 'Mild': .6, 'Moderate': 1.2, 'Severe': 1.9}[perio]
        score += .7 if smoking == 'Yes' else 0
        score += .8 if diabetes == 'Yes' else 0
        score += .3 if age >= 60 else 0
        prob = 1 / (1 + np.exp(-(score - 3.6)))
        urgent = 'Urgent' if rng.random() < prob else 'Non-Urgent'
        rows.append([age, sex, smoking, diabetes, pain, bleed, caries,
                     missing, hygiene, perio, urgent])
    return rows


def _config_hash():
    h = hashlib.sha256()
    h.update(repr(sorted(config.SYNTHETIC.items())).encode())
    h.update(sklearn.__version__.encode())
    return h.hexdigest()[:12]


def _base_features():
    train = synthetic_data()
    X = pd.DataFrame([r[:-1] for r in train], columns=config.FEATURES)
    y = pd.Series([r[-1] for r in train], name='treatment_urgency')
    return X, y


def _preprocessor():
    num = Pipeline([('imp', SimpleImputer(strategy='median')),
                    ('scale', StandardScaler())])
    cat = Pipeline([('imp', SimpleImputer(strategy='most_frequent')),
                    ('oh', OneHotEncoder(handle_unknown='ignore'))])
    return ColumnTransformer([('num', num, config.NUMS), ('cat', cat, config.CATS)])


def _train():
    X, y = _base_features()
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=config.SPLIT['test_size'],
        random_state=config.SPLIT['random_state'], stratify=y)
    estimators = {
        'Logistic Regression': LogisticRegression(max_iter=1000),
        'Decision Tree': DecisionTreeClassifier(max_depth=5, random_state=42),
        'Random Forest': RandomForestClassifier(n_estimators=180, max_depth=8, random_state=42),
        'Support Vector Machine': SVC(probability=True, random_state=42),
        'Gradient Boosting': GradientBoostingClassifier(random_state=42),
    }
    pipelines = {
        name: Pipeline([('prep', _preprocessor()), ('model', est)]).fit(X_train, y_train)
        for name, est in estimators.items()
    }
    return {'pipelines': pipelines, 'X_test': X_test, 'y_test': y_test}


def get_workspace(force=False):
    global _WORKSPACE
    if _WORKSPACE is not None and not force:
        return _WORKSPACE
    path = os.path.join(config.MODELS_DIR, f'ml-{_config_hash()}.joblib')
    if not force and os.path.exists(path):
        _WORKSPACE = joblib.load(path)
        return _WORKSPACE
    _WORKSPACE = _train()
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    joblib.dump(_WORKSPACE, path)
    return _WORKSPACE


def _coerce_values(data):
    vals = []
    for f in config.FEATURES:
        if f in config.NUMS:
            try:
                vals.append(int(data.get(f) or 0))
            except (TypeError, ValueError):
                vals.append(0)
        else:
            vals.append(data.get(f, ''))
    return vals


def risk_payload(data, model_name=None):
    ws = get_workspace()
    name = (model_name or config.DEFAULT_MODEL)
    pipe = ws['pipelines'].get(name) or ws['pipelines'][config.DEFAULT_MODEL]
    used_name = name if name in ws['pipelines'] else config.DEFAULT_MODEL
    input_df = pd.DataFrame([_coerce_values(data)], columns=config.FEATURES)
    pred = pipe.predict(input_df)[0]
    proba = float(pipe.predict_proba(input_df)[0][list(pipe.classes_).index(pred)])
    reasons = []
    if data.get('dental_pain') == 'Yes':
        reasons.append(('Dental pain', 'increases urgency signal'))
    if data.get('bleeding_gums') == 'Yes':
        reasons.append(('Bleeding gums', 'increases urgency signal'))
    if int(data.get('caries_count') or 0) >= 4:
        reasons.append(('Higher caries count', 'increases urgency signal'))
    if data.get('periodontal_status') in ['Moderate', 'Severe']:
        reasons.append(('Periodontal status', 'increases urgency signal'))
    if data.get('oral_hygiene') == 'Poor':
        reasons.append(('Poor oral hygiene', 'increases urgency signal'))
    if data.get('diabetes') == 'Yes':
        reasons.append(('Diabetes', 'included risk factor'))
    return {'prediction': pred, 'probability': round(proba * 100, 1),
            'model': used_name, 'reasons': reasons[:5]}


def model_metrics():
    # Hold-out test set metrics; not training-set reference numbers.
    ws = get_workspace()
    X_test, y_test = ws['X_test'], ws['y_test']
    out = []
    for name, pipe in ws['pipelines'].items():
        pred = pipe.predict(X_test)
        out.append({
            'model': name,
            'accuracy': round(accuracy_score(y_test, pred) * 100, 1),
            'precision': round(precision_score(y_test, pred, pos_label='Urgent') * 100, 1),
            'recall': round(recall_score(y_test, pred, pos_label='Urgent') * 100, 1),
            'f1': round(f1_score(y_test, pred, pos_label='Urgent') * 100, 1),
        })
    return out