import sqlite3

from . import config

BASE_SCHEMA = '''
CREATE TABLE IF NOT EXISTS patients(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT UNIQUE, name TEXT, age INTEGER, sex TEXT, phone TEXT,
    address TEXT, smoking TEXT, diabetes TEXT, dental_pain TEXT, bleeding_gums TEXT,
    caries_count INTEGER, missing_teeth INTEGER, oral_hygiene TEXT, periodontal_status TEXT,
    status TEXT DEFAULT 'Active', created_at TEXT
);
CREATE TABLE IF NOT EXISTS appointments(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT, patient_name TEXT, date TEXT, time TEXT, dentist TEXT,
    purpose TEXT, status TEXT DEFAULT 'Scheduled'
);
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT, role TEXT, email TEXT, status TEXT DEFAULT 'Active',
    password_hash TEXT
);
CREATE TABLE IF NOT EXISTS tooth_records(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL, tooth_no TEXT NOT NULL,
    status TEXT DEFAULT 'Healthy', notes TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS treatment_records(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL, visit_date TEXT NOT NULL, procedure TEXT NOT NULL,
    tooth_no TEXT, dentist TEXT, notes TEXT, created_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_tooth_patient ON tooth_records(patient_id);
CREATE INDEX IF NOT EXISTS idx_treat_patient ON treatment_records(patient_id);
CREATE INDEX IF NOT EXISTS idx_appt_patient ON appointments(patient_id);
'''

# Child tables rebuilt with real foreign keys pointing at patients(patient_id).
# Standard SQLite per-table rebuild (create new, copy, drop, rename). The parent
# (patients) keeps its schema, so its FK references are never invalidated.
FK_REBUILD = '''
CREATE TABLE tooth_records_new(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    tooth_no TEXT NOT NULL, status TEXT DEFAULT 'Healthy', notes TEXT, updated_at TEXT
);
INSERT INTO tooth_records_new SELECT id, patient_id, tooth_no, status, notes, updated_at FROM tooth_records;
DROP TABLE tooth_records;
ALTER TABLE tooth_records_new RENAME TO tooth_records;
CREATE INDEX IF NOT EXISTS idx_tooth_patient ON tooth_records(patient_id);

CREATE TABLE treatment_records_new(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id) ON DELETE CASCADE,
    visit_date TEXT NOT NULL, procedure TEXT NOT NULL,
    tooth_no TEXT, dentist TEXT, notes TEXT, created_at TEXT
);
INSERT INTO treatment_records_new
    SELECT id, patient_id, visit_date, procedure, tooth_no, dentist, notes, created_at
    FROM treatment_records;
DROP TABLE treatment_records;
ALTER TABLE treatment_records_new RENAME TO treatment_records;
CREATE INDEX IF NOT EXISTS idx_treat_patient ON treatment_records(patient_id);

CREATE TABLE appointments_new(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT REFERENCES patients(patient_id) ON DELETE SET NULL,
    patient_name TEXT, date TEXT, time TEXT, dentist TEXT,
    purpose TEXT, status TEXT DEFAULT 'Scheduled'
);
INSERT INTO appointments_new
    SELECT id, patient_id, patient_name, date, time, dentist, purpose, status
    FROM appointments;
DROP TABLE appointments;
ALTER TABLE appointments_new RENAME TO appointments;
CREATE INDEX IF NOT EXISTS idx_appt_patient ON appointments(patient_id);
'''

MIGRATIONS = {
    1: BASE_SCHEMA,
    3: FK_REBUILD,
}


def _table_columns(conn, table):
    return [r[1] for r in conn.execute(f'PRAGMA table_info({table})')]


def run_migrations(db_path=None):
    path = db_path or config.DB_PATH
    conn = sqlite3.connect(path)
    try:
        version = conn.execute('PRAGMA user_version').fetchone()[0]
        if version < 1:
            conn.executescript(MIGRATIONS[1])
            version = 1
        if version < 2 and 'password_hash' not in _table_columns(conn, 'users'):
            conn.execute('ALTER TABLE users ADD COLUMN password_hash TEXT')
            version = 2
        if version < 3:
            conn.executescript(MIGRATIONS[3])
            version = 3
        conn.execute(f'PRAGMA user_version = {version}')
        conn.commit()
    finally:
        conn.close()