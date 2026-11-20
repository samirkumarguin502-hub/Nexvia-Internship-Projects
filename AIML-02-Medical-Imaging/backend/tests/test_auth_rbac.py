import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core import security
from app.core.config import Settings

def setup_function():
    security.DB_PATH = __import__('pathlib').Path('test-auth.sqlite3')
    if security.DB_PATH.exists(): security.DB_PATH.unlink()

def teardown_function():
    if security.DB_PATH.exists(): security.DB_PATH.unlink()

def test_user_registration_and_admin_route_forbidden():
    with TestClient(app) as client:
        registered = client.post('/api/v1/auth/register', json={'email':'user@example.com','full_name':'Demo User','password':'StrongPass123!'})
        assert registered.status_code == 201
        token = registered.json()['access_token']
        headers = {'Authorization': f'Bearer {token}'}
        assert client.get('/api/v1/auth/me', headers=headers).json()['role'] == 'user'
        assert client.get('/api/v1/admin/users', headers=headers).status_code == 403
        assert client.get('/api/v1/monitoring/summary', headers=headers).status_code == 403
        assert client.post('/api/v1/inference/analyze', headers=headers).status_code == 422

def test_user_cannot_login_to_admin_portal():
    with TestClient(app) as client:
        client.post('/api/v1/auth/register', json={'email':'user@example.com','full_name':'Demo User','password':'StrongPass123!'})
        response = client.post('/api/v1/auth/login', json={'email':'user@example.com','password':'StrongPass123!','portal':'admin'})
        assert response.status_code == 403

def test_admin_can_access_admin_routes():
    with TestClient(app) as client:
        admin = security.create_user('admin@example.com', 'System Admin', 'AnotherStrongPass123!', 'admin')
        response = client.post('/api/v1/auth/login', json={'email':'admin@example.com','password':'AnotherStrongPass123!','portal':'admin'})
        assert response.status_code == 200
        headers = {'Authorization': f"Bearer {response.json()['access_token']}"}
        assert client.get('/api/v1/admin/users', headers=headers).status_code == 200
        assert client.get('/api/v1/monitoring/summary', headers=headers).status_code == 200
        assert client.patch(f"/api/v1/admin/users/{admin['id']}/status", headers=headers, json={'active': False}).status_code == 400
        assert client.patch('/api/v1/admin/users/999999/status', headers=headers, json={'active': False}).status_code == 404

def test_access_tokens_are_signed_hs256_jwts():
    token = security.issue_token({'id': 42, 'email': 'user@example.com', 'role': 'user'})
    assert len(token.split('.')) == 3
    assert security.decode_token(token)['sub'] == '42'
    header, payload, signature = token.split('.')
    corrupted = ('A' if signature[0] != 'A' else 'B') + signature[1:]
    with pytest.raises(ValueError):
        security.decode_token(f'{header}.{payload}.{corrupted}')

def test_production_requires_a_configured_jwt_secret():
    with pytest.raises(ValueError, match='JWT_SECRET_KEY'):
        Settings(ENVIRONMENT='production', JWT_SECRET_KEY='')
