from flask import Blueprint, flash, render_template, request, redirect, url_for

from .. import db
from ..auth import login_required, role_required

bp = Blueprint('patients', __name__)

WRITER_ROLES = ('Dentist', 'Administrator')


@bp.route('/patients')
@login_required
def patients():
    search = (request.args.get('q') or '').strip()
    page = request.args.get('page', 1, type=int)
    page = max(page, 1)
    data = db.patient_page(search=search, page=page, per_page=25)
    return render_template('patients.html', **data)


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


@bp.route('/patients/<int:pid>/delete', methods=['POST'])
@login_required
@role_required(*WRITER_ROLES)
def patient_delete(pid):
    if not db.delete_patient(pid):
        return 'Patient not found', 404
    flash('Patient record deleted.')
    return redirect(url_for('patients.patients'))