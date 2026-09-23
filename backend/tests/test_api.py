"""Regression routes; fixtures always use an isolated SQLite database."""
from .test_readiness import app, sign_in


def test_health_profile_and_unknown(app):
    c = sign_in(app)
    assert c.get('/api/health').json()['employees'] == 200
    assert c.get('/api/employees?limit=200').json()['total'] == 200
    assert c.get('/api/employees/E0002').status_code == 200
    assert c.get('/api/employees/NOPE').status_code == 404


def test_invalid_import(app):
    c = sign_in(app)
    assert c.post('/api/import', json={'employees': [{'employee_id': 'broken'}]}).status_code == 422
