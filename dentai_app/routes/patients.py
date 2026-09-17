from flask import Blueprint, render_template, request, redirect, url_for

from .. import db
from ..auth import login_required, role_required

bp = Blueprint('patients', __name__)

WRITER_ROLES = ('Dentist', 'Administrator')


@bp.route('/patients')
@login_required
def patients():
    rows = db.list_patients()
    return render_template('patients.html', patients=rows)


@bp.route('/patients/new', methods=['GET', 'POST'])
@login_required
@role_required(*WRITER_ROLES)
def patient_new():
    if request.method == 'POST':
        db.create_patient(request.form)
        return redirect(url_for('patients.patients'))
    return render_template('patient_form.html', patient=None)


@bp.route('/patients/<int:pid>/edit', methods=['GET', 'POST'])
@login_required
@role_required(*WRITER_ROLES)
def patient_edit(pid):
    patient = db.get_patient(pid)
    if not patient:
        return 'Patient not found', 404
    if request.method == 'POST':
        db.update_patient(pid, request.form)
        return redirect(url_for('patients.patients'))
    return render_template('patient_form.html', patient=patient)