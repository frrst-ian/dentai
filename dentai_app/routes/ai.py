from flask import Blueprint, render_template, request

from .. import db, ml
from ..auth import login_required

bp = Blueprint('ai', __name__)


@bp.route('/patients/<int:pid>/ai')
@login_required
def patient_ai(pid):
    patient = db.get_patient(pid)
    if not patient:
        return 'Patient not found', 404
    return render_template('ai.html', patient=patient)


@bp.route('/risk')
@login_required
def risk():
    patients = db.list_patients()
    return render_template('risk.html', patients=patients)


@bp.route('/predict', methods=['POST'])
@login_required
def predict():
    data = request.form.to_dict()
    result = ml.risk_payload(data, data.get('model'))
    pid = None
    row = db.get_patient_by_code(data.get('patient_id') or '')
    if row:
        pid = row['id']
    return render_template('result.html',
                           result=result,
                           patient=data.get('patient_name') or 'Current Patient',
                           pid=pid)