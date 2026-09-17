import sqlite3
from contextlib import contextmanager
from datetime import datetime

from werkzeug.security import generate_password_hash

from . import config

DB_PATH = config.DB_PATH


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


@contextmanager
def get_conn():
    conn = connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def bootstrap():
    from .migrations import run_migrations
    run_migrations(DB_PATH)
    seed_data()


def seed_data():
    with get_conn() as c:
        if c.execute('SELECT COUNT(*) FROM patients').fetchone()[0] == 0:
            sample = [
                ('P-001', 'Juan Dela Cruz', 25, 'Male', '09170000001', 'Sample Address', 'No', 'No', 'Yes', 'No', 3, 0, 'Fair', 'Healthy'),
                ('P-002', 'Maria Reyes', 42, 'Female', '09170000002', 'Sample Address', 'No', 'No', 'No', 'Yes', 1, 2, 'Good', 'Mild'),
                ('P-003', 'Carlos Santos', 37, 'Male', '09170000003', 'Sample Address', 'Yes', 'No', 'Yes', 'Yes', 6, 3, 'Poor', 'Moderate'),
                ('P-004', 'Ana Lopez', 29, 'Female', '09170000004', 'Sample Address', 'No', 'No', 'No', 'No', 0, 0, 'Good', 'Healthy'),
                ('P-005', 'Pedro Garcia', 50, 'Male', '09170000005', 'Sample Address', 'Yes', 'Yes', 'Yes', 'Yes', 8, 5, 'Poor', 'Severe'),
            ]
            c.executemany(
                'INSERT INTO patients(patient_id,name,age,sex,phone,address,smoking,diabetes,'
                'dental_pain,bleeding_gums,caries_count,missing_teeth,oral_hygiene,'
                'periodontal_status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                [(*p, datetime.now().isoformat()) for p in sample])
        if c.execute('SELECT COUNT(*) FROM users').fetchone()[0] == 0:
            c.executemany(
                'INSERT INTO users(name,role,email,password_hash,status) VALUES (?,?,?,?,?)',
                [(n, r, e, generate_password_hash(pw), 'Active') for n, r, e, pw in config.DEMO_USERS])
        else:
            c.executemany(
                'UPDATE users SET password_hash=? WHERE email=? AND '
                '(password_hash IS NULL OR password_hash="")',
                [(generate_password_hash(pw), e) for _, _, e, pw in config.DEMO_USERS])


def list_patients(limit=None):
    sql = 'SELECT * FROM patients ORDER BY id DESC'
    with get_conn() as c:
        rows = c.execute(sql).fetchall() if limit is None else c.execute(sql + ' LIMIT ?', (limit,)).fetchall()
    return rows


def get_patient(pid):
    with get_conn() as c:
        row = c.execute('SELECT * FROM patients WHERE id=?', (pid,)).fetchone()
    return row


def get_patient_by_code(code):
    with get_conn() as c:
        row = c.execute('SELECT * FROM patients WHERE patient_id=?', (code,)).fetchone()
    return row


def create_patient(f):
    patient_id = f.get('patient_id') or f"P-{int(datetime.now().timestamp()) % 100000:05d}"
    with get_conn() as c:
        c.execute(
            'INSERT INTO patients(patient_id,name,age,sex,phone,address,smoking,diabetes,'
            'dental_pain,bleeding_gums,caries_count,missing_teeth,oral_hygiene,'
            'periodontal_status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            (patient_id, f.get('name'), int(f.get('age') or 0), f.get('sex'), f.get('phone'),
             f.get('address'), f.get('smoking'), f.get('diabetes'), f.get('dental_pain'),
             f.get('bleeding_gums'), int(f.get('caries_count') or 0),
             int(f.get('missing_teeth') or 0), f.get('oral_hygiene'),
             f.get('periodontal_status'), datetime.now().isoformat()))
    return patient_id


def update_patient(pid, f):
    with get_conn() as c:
        c.execute(
            'UPDATE patients SET name=?,age=?,sex=?,phone=?,address=?,smoking=?,diabetes=?,'
            'dental_pain=?,bleeding_gums=?,caries_count=?,missing_teeth=?,oral_hygiene=?,'
            'periodontal_status=? WHERE id=?',
            (f.get('name'), int(f.get('age') or 0), f.get('sex'), f.get('phone'),
             f.get('address'), f.get('smoking'), f.get('diabetes'), f.get('dental_pain'),
             f.get('bleeding_gums'), int(f.get('caries_count') or 0),
             int(f.get('missing_teeth') or 0), f.get('oral_hygiene'),
             f.get('periodontal_status'), pid))


def dashboard_stats():
    counts = {}
    with get_conn() as c:
        for table in ('patients', 'appointments', 'users'):
            counts[table] = c.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
    return counts


def recent_patients(limit=5):
    with get_conn() as c:
        rows = c.execute('SELECT * FROM patients ORDER BY id DESC LIMIT ?', (limit,)).fetchall()
    return rows


def list_tooth_records(patient_code):
    with get_conn() as c:
        rows = c.execute('SELECT * FROM tooth_records WHERE patient_id=? ORDER BY tooth_no',
                         (patient_code,)).fetchall()
    return rows


def save_tooth(patient_code, tooth_no, status, notes):
    with get_conn() as c:
        c.execute('DELETE FROM tooth_records WHERE patient_id=? AND tooth_no=?',
                  (patient_code, tooth_no))
        c.execute('INSERT INTO tooth_records(patient_id,tooth_no,status,notes,updated_at) '
                  'VALUES (?,?,?,?,?)',
                  (patient_code, tooth_no, status, notes, datetime.now().isoformat()))


def list_treatment_records(patient_code):
    with get_conn() as c:
        rows = c.execute('SELECT * FROM treatment_records WHERE patient_id=? '
                         'ORDER BY visit_date DESC, id DESC', (patient_code,)).fetchall()
    return rows


def add_treatment(patient_code, f):
    with get_conn() as c:
        c.execute('INSERT INTO treatment_records(patient_id,visit_date,procedure,tooth_no,'
                  'dentist,notes,created_at) VALUES (?,?,?,?,?,?,?)',
                  (patient_code, f.get('visit_date'), f.get('procedure'),
                   f.get('tooth_no') or None, f.get('dentist'), f.get('notes'),
                   datetime.now().isoformat()))


def list_appointments():
    with get_conn() as c:
        rows = c.execute('SELECT * FROM appointments ORDER BY date, time').fetchall()
    return rows


def add_appointment(f):
    with get_conn() as c:
        c.execute('INSERT INTO appointments(patient_id,patient_name,date,time,dentist,purpose,status) '
                  'VALUES (?,?,?,?,?,?,?)',
                  (f.get('patient_id'), f.get('patient_name'), f.get('date'), f.get('time'),
                   f.get('dentist'), f.get('purpose'), 'Scheduled'))


def get_user_by_email(email):
    with get_conn() as c:
        row = c.execute('SELECT * FROM users WHERE email=?', (email.lower(),)).fetchone()
    return row


def list_users():
    with get_conn() as c:
        rows = c.execute('SELECT * FROM users ORDER BY id').fetchall()
    return rows


def periodontal_counts():
    with get_conn() as c:
        rows = c.execute('SELECT periodontal_status, COUNT(*) n FROM patients '
                         'GROUP BY periodontal_status').fetchall()
    return {r['periodontal_status']: r['n'] for r in rows}