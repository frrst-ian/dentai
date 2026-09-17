import csv
import io
import json
from datetime import datetime

from flask import Blueprint, jsonify, request

from .. import db, ml
from ..auth import login_required, role_required

bp = Blueprint('api', __name__)


@bp.route('/api/predict', methods=['POST'])
@login_required
def api_predict():
    return jsonify(ml.risk_payload(request.json or {}))


@bp.route('/api/import_csv', methods=['POST'])
@login_required
@role_required('Dentist', 'Administrator')
def import_csv():
    if 'file' not in request.files:
        return jsonify({'error': 'No CSV file'}), 400
    text = request.files['file'].read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(text))
    n = 0
    for r in reader:
        try:
            pid = r.get('patient_id') or r.get('Patient ID') or f"IMP-{n + 1:04d}"
            name = r.get('name') or r.get('Name') or 'Imported Patient'
            db.create_patient({
                'patient_id': pid,
                'name': name,
                'age': int(r.get('age') or r.get('Age') or 0),
                'sex': r.get('sex') or r.get('Sex') or 'Unknown',
                'smoking': r.get('smoking') or r.get('Smoking') or 'No',
                'diabetes': r.get('diabetes') or r.get('Diabetes') or 'No',
                'dental_pain': r.get('dental_pain') or r.get('Dental pain') or 'No',
                'bleeding_gums': r.get('bleeding_gums') or r.get('Bleeding gums') or 'No',
                'caries_count': int(r.get('caries_count') or r.get('Caries count') or 0),
                'missing_teeth': int(r.get('missing_teeth') or r.get('Missing teeth') or 0),
                'oral_hygiene': r.get('oral_hygiene') or r.get('Oral hygiene') or 'Good',
                'periodontal_status': r.get('periodontal_status') or r.get('Periodontal status') or 'Healthy',
            })
            n += 1
        except Exception:
            continue
    return jsonify({'imported': n})