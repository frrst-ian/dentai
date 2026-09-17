import io

import pytest

from dentai_app import db

ADMIN = ('admin@dentalai.local', 'admin123')
DENTIST = ('dentist@dentalai.local', 'dentist123')
EVALUATOR = ('evaluator@dentalai.local', 'evaluator123')


def login(client, email, password):
    return client.post('/login', data={'email': email, 'password': password})


@pytest.fixture()
def admin_client(client):
    login(client, *ADMIN)
    return client


def _create_patient(client):
    client.post('/patients/new', data={
        'patient_id': 'TEST-001', 'name': 'Test Patient', 'age': '30', 'sex': 'Male',
        'phone': '', 'address': '', 'smoking': 'No', 'diabetes': 'No', 'dental_pain': 'No',
        'bleeding_gums': 'No', 'caries_count': '1', 'missing_teeth': '0',
        'oral_hygiene': 'Good', 'periodontal_status': 'Healthy',
    })
    for row in db.list_patients():
        if row['patient_id'] == 'TEST-001':
            return row['id']
    raise AssertionError('test patient not created')


# ---- auth ----

def test_login_page_renders(client):
    assert client.get('/').status_code == 200


def test_login_redirects_to_dashboard(client):
    r = login(client, *ADMIN)
    assert r.status_code == 302
    assert r.headers['Location'] == '/dashboard'


def test_login_rejects_bad_password(client):
    login(client, ADMIN[0], 'wrong-password')
    page = client.get('/', follow_redirects=True)
    assert b'Invalid email or password' in page.data


def test_dashboard_requires_login(client):
    assert client.get('/dashboard').status_code == 302


def test_logout_clears_session(admin_client):
    assert admin_client.get('/dashboard').status_code == 200
    admin_client.get('/logout')
    assert admin_client.get('/dashboard').status_code == 302


# ---- dashboard / patients ----

def test_dashboard(admin_client):
    r = admin_client.get('/dashboard')
    assert r.status_code == 200
    assert b'Patients' in r.data


def test_patients_page(admin_client):
    r = admin_client.get('/patients')
    assert r.status_code == 200
    assert b'Patient Management' in r.data


def test_create_patient(admin_client):
    pid = _create_patient(admin_client)
    assert pid is not None


def test_edit_patient(admin_client):
    pid = _create_patient(admin_client)
    assert admin_client.get(f'/patients/{pid}/edit').status_code == 200
    r = admin_client.post(f'/patients/{pid}/edit', data={
        'name': 'Renamed Patient', 'age': '31', 'sex': 'Female', 'phone': '',
        'address': '', 'smoking': 'No', 'diabetes': 'No', 'dental_pain': 'Yes',
        'bleeding_gums': 'No', 'caries_count': '2', 'missing_teeth': '0',
        'oral_hygiene': 'Fair', 'periodontal_status': 'Mild',
    })
    assert r.status_code == 302
    assert db.get_patient(pid)['name'] == 'Renamed Patient'


def test_patient_new_denies_evaluator(client):
    login(client, *EVALUATOR)
    assert client.post('/patients/new', data={'name': 'X'}).status_code == 403


# ---- dental chart ----

def test_chart_page(admin_client):
    pid = _create_patient(admin_client)
    r = admin_client.get(f'/patients/{pid}/chart')
    assert r.status_code == 200
    assert b'Dental Chart' in r.data


def test_save_tooth(admin_client):
    pid = _create_patient(admin_client)
    r = admin_client.post(f'/patients/{pid}/tooth/11',
                          data={'status': 'Caries', 'notes': 'occlusal decay'})
    assert r.status_code == 302
    records = db.list_tooth_records('TEST-001')
    assert any(x['tooth_no'] == '11' and x['status'] == 'Caries' for x in records)


def test_save_tooth_rejects_invalid_number(admin_client):
    pid = _create_patient(admin_client)
    assert admin_client.post(f'/patients/{pid}/tooth/99',
                             data={'status': 'Caries'}).status_code == 400


def test_save_tooth_denies_evaluator(client):
    login(client, *EVALUATOR)
    row = db.list_patients()[0]
    assert client.post(f'/patients/{row["id"]}/tooth/11',
                       data={'status': 'Caries'}).status_code == 403


def test_add_treatment_record(admin_client):
    pid = _create_patient(admin_client)
    r = admin_client.post(f'/patients/{pid}/records', data={
        'visit_date': '2026-09-17', 'procedure': 'Composite filling',
        'tooth_no': '12', 'dentist': 'Dr. Maria Santos', 'notes': '',
    })
    assert r.status_code == 302
    records = db.list_treatment_records('TEST-001')
    assert any(x['procedure'] == 'Composite filling' for x in records)


# ---- AI ----

def test_ai_page(admin_client):
    pid = _create_patient(admin_client)
    assert admin_client.get(f'/patients/{pid}/ai').status_code == 200


def test_risk_page(admin_client):
    assert admin_client.get('/risk').status_code == 200


def test_predict(admin_client):
    _create_patient(admin_client)
    r = admin_client.post('/predict', data={
        'patient_id': 'TEST-001', 'patient_name': 'Test Patient', 'age': '30',
        'sex': 'Male', 'smoking': 'No', 'diabetes': 'No', 'dental_pain': 'Yes',
        'bleeding_gums': 'No', 'caries_count': '5', 'missing_teeth': '1',
        'oral_hygiene': 'Poor', 'periodontal_status': 'Severe', 'model': 'Random Forest',
    })
    assert r.status_code == 200
    assert b'Prediction' in r.data
    assert b'Probability' in r.data


# ---- appointments / reports / users ----

def test_appointments_page(admin_client):
    assert admin_client.get('/appointments').status_code == 200


def test_add_appointment(admin_client):
    _create_patient(admin_client)
    r = admin_client.post('/appointments/add', data={
        'patient_id': 'TEST-001', 'patient_name': 'Test Patient',
        'date': '2026-09-20', 'time': '09:00', 'dentist': 'Dr. Maria Santos',
        'purpose': 'Checkup',
    })
    assert r.status_code == 302
    assert len(db.list_appointments()) == 1


def test_reports(admin_client):
    r = admin_client.get('/reports')
    assert r.status_code == 200
    assert b'Accuracy' in r.data


def test_users_admin_only(admin_client):
    assert admin_client.get('/users').status_code == 200


def test_users_denies_dentist(client):
    login(client, *DENTIST)
    assert client.get('/users').status_code == 403


# ---- JSON API ----

def test_api_predict(admin_client):
    r = admin_client.post('/api/predict', json={
        'age': '45', 'sex': 'Female', 'smoking': 'Yes', 'diabetes': 'No',
        'dental_pain': 'Yes', 'bleeding_gums': 'Yes', 'caries_count': '6',
        'missing_teeth': '3', 'oral_hygiene': 'Poor', 'periodontal_status': 'Severe',
    })
    assert r.status_code == 200
    body = r.get_json()
    assert body['prediction'] in ('Urgent', 'Non-Urgent')
    assert body['model'] in ('Random Forest', 'Logistic Regression')


def test_api_predict_partial_payload(admin_client):
    r = admin_client.post('/api/predict', json={'dental_pain': 'Yes'})
    assert r.status_code == 200
    assert r.get_json()['prediction'] in ('Urgent', 'Non-Urgent')


def test_import_csv(admin_client):
    csv_data = b'patient_id,name,age,sex\nCSV-001,Imported Patient,40,Male\n'
    r = admin_client.post('/api/import_csv',
                          data={'file': (io.BytesIO(csv_data), 'patients.csv')},
                          content_type='multipart/form-data')
    assert r.status_code == 200
    assert r.get_json() == {'imported': 1}

    r = admin_client.post('/api/import_csv')
    assert r.status_code == 400


def test_import_csv_denies_evaluator(client):
    login(client, *EVALUATOR)
    r = client.post('/api/import_csv', data={'file': (io.BytesIO(b''), 'x.csv')},
                    content_type='multipart/form-data')
    assert r.status_code == 403