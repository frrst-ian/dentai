from flask import Blueprint, flash, redirect, render_template, request, url_for

from .. import db, ml
from ..auth import login_required, role_required

bp = Blueprint('admin', __name__)

STATUS_OPTIONS = ['Scheduled', 'Completed', 'Cancelled', 'No-show']


@bp.route('/dashboard')
@login_required
def dashboard():
    stats = db.dashboard_stats()
    recent = db.recent_patients(5)
    upcoming = db.list_appointments(status='Scheduled', limit=3)
    scheduled = db.appointment_status_counts().get('Scheduled', 0)
    return render_template('dashboard.html', stats=stats, recent=recent,
                           upcoming=upcoming, scheduled=scheduled)


@bp.route('/appointments')
@login_required
def appointments():
    status_filter = request.args.get('status') or ''
    if status_filter not in STATUS_OPTIONS:
        status_filter = ''
    rows = db.list_appointments(status=status_filter)
    patients = db.list_patients()
    status_counts = db.appointment_status_counts()
    return render_template(
        'appointments.html', appointments=rows, patients=patients,
        status_filter=status_filter, status_options=STATUS_OPTIONS,
        status_counts=status_counts, total_appointments=sum(status_counts.values()))


@bp.route('/appointments/add', methods=['POST'])
@login_required
@role_required('Dentist', 'Administrator')
def appointment_add():
    db.add_appointment(request.form)
    flash('Appointment booked.')
    return redirect(url_for('admin.appointments'))


@bp.route('/appointments/<int:aid>/status', methods=['POST'])
@login_required
@role_required('Dentist', 'Administrator')
def appointment_status(aid):
    status = request.form.get('status')
    if not db.update_appointment_status(aid, status):
        return 'Invalid status or appointment not found', 400
    flash(f'Appointment #{aid} marked {status}.')
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