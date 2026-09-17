from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from .. import db
from werkzeug.security import check_password_hash

from ..auth import login_required

bp = Blueprint('auth', __name__)


@bp.route('/')
def login():
    if session.get('user_id'):
        return redirect(url_for('admin.dashboard'))
    return render_template('login.html')


@bp.route('/login', methods=['POST'])
def do_login():
    email = (request.form.get('email') or '').strip().lower()
    password = request.form.get('password') or ''
    user = db.get_user_by_email(email)
    if not user or not user['password_hash'] or not check_password_hash(user['password_hash'], password):
        flash('Invalid email or password.')
        return redirect(url_for('auth.login'))
    session.clear()
    session['user_id'] = user['id']
    session['name'] = user['name']
    session['role'] = user['role']
    session['email'] = user['email']
    return redirect(url_for('admin.dashboard'))


@bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('auth.login'))