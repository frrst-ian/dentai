from flask import Blueprint, redirect, render_template, request, url_for

from .. import db, ml
from ..auth import login_required, role_required

bp = Blueprint('admin', __name__)


@bp.route('/dashboard')
@login_required
def dashboard():
    stats = db.dashboard_stats()
    recent = db.recent_patients(5)
    return render_template('dashboard.html', stats=stats, recent=recent)


@bp.route('/appointments')
@login_required
def appointments():
    rows = db.list_appointments()
    patients = db.list_patients()
    return render_template('appointments.html', appointments=rows, patients=patients)


@bp.route('/appointments/add', methods=['POST'])
@login_required
@role_required('Dentist', 'Administrator')
def appointment_add():
    db.add_appointment(request.form)
    return redirect(url_for('admin.appointments'))


@bp.route('/appointments/<int:aid>/status', methods=['POST'])
@login_required
@role_required('Dentist', 'Administrator')
def appointment_status(aid):
    if not db.update_appointment_status(aid, request.form.get('status')):
        return 'Invalid status or appointment not found', 400
    return redirect(url_for('admin.appointments'))


@bp.route('/reports')
@login_required
def reports():
    counts = db.periodontal_counts()
    count_max = max(counts.values(), default=1) or 1
    return render_template('reports.html', metrics=ml.model_metrics(), counts=counts, count_max=count_max)


@bp.route('/users')
@login_required
@role_required('Administrator')
def users():
    rows = db.list_users()
    return render_template('users.html', users=rows)