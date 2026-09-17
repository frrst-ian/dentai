import pytest

from dentai_app import create_app


@pytest.fixture()
def app(tmp_path):
    db_file = tmp_path / 'test.db'
    app = create_app({
        'TESTING': True,
        'DB_PATH': str(db_file),
        'SECRET_KEY': 'test-secret',
    })
    return app


@pytest.fixture()
def client(app):
    return app.test_client()