import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATES_DIR = os.path.join(BASE, 'templates')
STATIC_DIR = os.path.join(BASE, 'static')
MODELS_DIR = os.path.join(BASE, 'models')

DB_PATH = os.environ.get('DENTAI_DB', os.path.join(BASE, 'dental_ai.db'))
SECRET_KEY = os.environ.get('DENTAI_SECRET', 'dental-ai-demo-change-this-secret')

DEFAULT_MODEL = 'Random Forest'

FEATURES = ['age', 'sex', 'smoking', 'diabetes', 'dental_pain', 'bleeding_gums',
            'caries_count', 'missing_teeth', 'oral_hygiene', 'periodontal_status']
CATS = ['sex', 'smoking', 'diabetes', 'dental_pain', 'bleeding_gums',
        'oral_hygiene', 'periodontal_status']
NUMS = ['age', 'caries_count', 'missing_teeth']

FDI_UPPER = list(range(11, 19)) + list(range(21, 29))
FDI_LOWER = list(range(41, 49)) + list(range(31, 39))
ALL_TEETH = FDI_UPPER + FDI_LOWER

TOOTH_STATUSES = ['Healthy', 'Caries', 'Filled', 'Missing', 'Extracted',
                  'Root Canal', 'Crown', 'Implant', 'Impacted']

SYNTHETIC = {'n': 700, 'seed': 42}
SPLIT = {'test_size': 0.25, 'random_state': 42}

DEMO_USERS = [
    ('Dr. Maria Santos', 'Dentist', 'dentist@dentalai.local', 'dentist123'),
    ('System Administrator', 'Administrator', 'admin@dentalai.local', 'admin123'),
    ('Research Evaluator', 'Evaluator', 'evaluator@dentalai.local', 'evaluator123'),
]