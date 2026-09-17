import pytest

from dentai_app import create_app, db


@pytest.fixture(scope='session')
def app(tmp_path_factory):
    db_file = tmp_path_factory.mktemp('data') / 'test.db'
    app = create_app({
        'TESTING': True,
        'DB_PATH': str(db_file),
        'SECRET_KEY': 'test-secret',
    })
    return app


@pytest.fixture(autouse=True)
def _clean_db(app):
    """Give every test a fresh seeded database without rebuilding the app."""
    with db.get_conn() as c:
        for table in ('tooth_records', 'treatment_records', 'appointments', 'patients', 'users'):
            c.execute(f'DELETE FROM {table}')
    db.seed_data()
    yield


@pytest.fixture()
def client(app):
    return app.test_client()