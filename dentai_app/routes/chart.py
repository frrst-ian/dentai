from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import config, db
from ..auth import login_required, role_required

bp = Blueprint('chart', __name__)

WRITER_ROLES = ('Dentist', 'Administrator')


@bp.route('/patients/<int:pid>/chart')
@login_required
def patient_chart(pid):
    patient = db.get_patient(pid)
    if not patient:
        return 'Patient not found', 404
    rows = db.list_tooth_records(patient['patient_id'])
    records = db.list_treatment_records(patient['patient_id'])
    tooth_map = {r['tooth_no']: r for r in rows}
    return render_template(
        'chart.html', patient=patient, tooth_map=tooth_map, records=records,
        upper=config.FDI_UPPER, lower=config.FDI_LOWER, all_teeth=config.ALL_TEETH,
        statuses=config.TOOTH_STATUSES)


@bp.route('/patients/<int:pid>/tooth/<tooth_no>', methods=['POST'])
@login_required
@role_required(*WRITER_ROLES)
def save_tooth(pid, tooth_no):
    if tooth_no not in {str(x) for x in config.ALL_TEETH}:
        return 'Invalid tooth number', 400
    patient = db.get_patient(pid)
    if not patient:
        return 'Patient not found', 404
    status = request.form.get('status') or 'Healthy'
    if status not in config.TOOTH_STATUSES:
        status = 'Healthy'
    db.save_tooth(patient['patient_id'], tooth_no, status, request.form.get('notes') or '')
    flash(f'Tooth {tooth_no} record saved.')
    return redirect(url_for('chart.patient_chart', pid=pid))


@bp.route('/patients/<int:pid>/records', methods=['POST'])
@login_required
@role_required(*WRITER_ROLES)
def add_treatment_record(pid):
    patient = db.get_patient(pid)
    if not patient:
        return 'Patient not found', 404
    db.add_treatment(patient['patient_id'], request.form)
    flash('Treatment record added.')
    return redirect(url_for('chart.patient_chart', pid=pid))