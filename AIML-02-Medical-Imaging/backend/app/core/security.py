"""SQLite account storage and JWT bearer-token helpers."""

import base64
import hashlib
import hmac
import os
import sqlite3
import time

from contextlib import contextmanager
from pathlib import Path
from typing import Any

import jwt

from app.core.config import settings


DB_PATH = Path(settings.AUTH_DB_PATH)

SECRET = (
    settings.JWT_SECRET_KEY.encode()
    if settings.JWT_SECRET_KEY
    else os.urandom(32)
)

if settings.ENVIRONMENT.lower() in ('production', 'prod') and not settings.JWT_SECRET_KEY:
    raise RuntimeError('JWT_SECRET_KEY is required in production')

TOKEN_TTL = settings.ACCESS_TOKEN_MINUTES * 60

JWT_ALGORITHM = 'HS256'
JWT_ISSUER = 'aiml-02-medical-imaging'
JWT_AUDIENCE = 'aiml-02-api'


@contextmanager
def _db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)

    try:
        conn.row_factory = sqlite3.Row
        conn.execute('PRAGMA foreign_keys = ON')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','admin')),
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                active INTEGER DEFAULT 1
            )
        ''')

        conn.execute('''
            CREATE TABLE IF NOT EXISTS studies (
                study_id TEXT PRIMARY KEY,
                owner_id INTEGER NOT NULL REFERENCES users(id),
                stored_name TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                content_type TEXT NOT NULL,
                modality TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL DEFAULT 'uploaded',
                orthanc_instance_id TEXT
            )
        ''')

        columns = {
            row['name']
            for row in conn.execute('PRAGMA table_info(studies)')
        }

        if 'orthanc_instance_id' not in columns:
            conn.execute(
                'ALTER TABLE studies ADD COLUMN orthanc_instance_id TEXT'
            )

        yield conn
        conn.commit()

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def hash_password(password: str) -> str:
    """Preserve the original password-hash storage format."""
    salt = os.urandom(16)

    digest = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode(),
        salt,
        310_000,
    )

    return (
        base64.urlsafe_b64encode(salt).decode()
        + '.'
        + base64.urlsafe_b64encode(digest).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_s, digest_s = stored.split('.', 1)

        salt = base64.urlsafe_b64decode(salt_s.encode())
        expected = base64.urlsafe_b64decode(digest_s.encode())

        actual = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt,
            310_000,
        )

        return hmac.compare_digest(actual, expected)

    except (ValueError, TypeError):
        return False


def create_user(
    email: str,
    full_name: str,
    password: str,
    role: str = 'user',
) -> dict[str, Any]:

    if role not in ('user', 'admin'):
        raise ValueError('Role must be user or admin')

    with _db() as conn:
        cur = conn.execute(
            '''
            INSERT INTO users(email,full_name,password_hash,role)
            VALUES(?,?,?,?)
            ''',
            (
                email.lower().strip(),
                full_name.strip(),
                hash_password(password),
                role,
            ),
        )

        row = conn.execute(
            '''
            SELECT id,email,full_name,role,active
            FROM users WHERE id=?
            ''',
            (cur.lastrowid,),
        ).fetchone()

        return dict(row)


def get_user_by_email(email: str):
    with _db() as conn:
        row = conn.execute(
            'SELECT * FROM users WHERE email=?',
            (email.lower().strip(),),
        ).fetchone()

        return dict(row) if row else None


def get_user_by_id(user_id: int):
    with _db() as conn:
        row = conn.execute(
            '''
            SELECT id,email,full_name,role,active,created_at
            FROM users WHERE id=?
            ''',
            (user_id,),
        ).fetchone()

        return dict(row) if row else None


def list_users():
    with _db() as conn:
        return [
            dict(row)
            for row in conn.execute(
                '''
                SELECT id,email,full_name,role,active,created_at
                FROM users ORDER BY id DESC
                '''
            )
        ]


def update_user_active(user_id: int, active: bool):
    with _db() as conn:
        cur = conn.execute(
            'UPDATE users SET active=? WHERE id=?',
            (1 if active else 0, user_id),
        )

        return cur.rowcount > 0


def count_users() -> int:
    with _db() as conn:
        return conn.execute(
            'SELECT COUNT(*) FROM users'
        ).fetchone()[0]


def issue_token(user: dict) -> str:
    now = int(time.time())

    payload = {
        'sub': str(user['id']),
        'email': user['email'],
        'role': user['role'],
        'iat': now,
        'exp': now + TOKEN_TTL,
        'iss': JWT_ISSUER,
        'aud': JWT_AUDIENCE,
    }

    return jwt.encode(
        payload,
        SECRET,
        algorithm=JWT_ALGORITHM,
        headers={'typ': 'JWT'},
    )


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            SECRET,
            algorithms=[JWT_ALGORITHM],
            issuer=JWT_ISSUER,
            audience=JWT_AUDIENCE,
            options={
                'require': [
                    'sub',
                    'email',
                    'role',
                    'iat',
                    'exp',
                    'iss',
                    'aud',
                ],
            },
        )

        if not str(payload['sub']).isdigit():
            raise ValueError('Invalid subject')

        if payload['role'] not in ('user', 'admin'):
            raise ValueError('Invalid role')

        return payload

    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise ValueError(
            'Invalid or expired access token'
        ) from exc


def bootstrap_admin():
    email = settings.ADMIN_EMAIL
    password = settings.ADMIN_PASSWORD

    if email and password and not get_user_by_email(email):
        create_user(
            email,
            settings.ADMIN_FULL_NAME,
            password,
            'admin',
        )