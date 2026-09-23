from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import sqlite3
import time
from pathlib import Path
from threading import RLock

from fastapi import HTTPException, Request

COOKIE_NAME = 'cq_session'


class AuthStore:
    def __init__(self, path: str):
        if path != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, salt TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL, employee_id TEXT);
            CREATE TABLE IF NOT EXISTS sessions (token_hash TEXT PRIMARY KEY, username TEXT NOT NULL, csrf TEXT NOT NULL, expires REAL NOT NULL);
        ''')
        self.failures = {}
        self._dummy = self._hash('invalid', '0' * 32)

    @staticmethod
    def _hash(password, salt):
        return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 240000).hex()

    def add_user(self, username, password, role, employee_id=None):
        if role not in ('employee', 'hr') or len(password) < 12 or (role == 'employee' and not employee_id):
            raise ValueError('Use a valid role, employee ID and a password with at least 12 characters')
        salt = secrets.token_hex(16)
        with self.lock, self.db:
            self.db.execute('INSERT OR REPLACE INTO users VALUES (?, ?, ?, ?, ?)', (username, salt, self._hash(password, salt), role, employee_id))
            self.db.execute('DELETE FROM sessions WHERE username=?', (username,))

    def provision_env(self):
        for role, employee_id in [('hr', None), ('employee', os.getenv('CQ_EMPLOYEE_ID', 'E0002'))]:
            password = os.getenv(f'CQ_{role.upper()}_PASSWORD')
            if password:
                self.add_user(role, password, role, employee_id)

    def login(self, username, password, client_ip):
        with self.lock:
            now = time.time()
            self.failures = {k: [t for t in ts if t > now - 60] for k, ts in self.failures.items() if any(t > now - 60 for t in ts)}
            attempts = self.failures.get(client_ip, [])
            if len(attempts) >= 10:
                raise HTTPException(429, detail='Too many login attempts. Try again in one minute.')
            self.failures[client_ip] = attempts + [now]
            user = self.db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
            actual = self._hash(password, user['salt'] if user else '0' * 32)
            if not hmac.compare_digest(actual, user['password_hash'] if user else self._dummy) or not user:
                raise HTTPException(401, detail='Incorrect username or password')
            token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
            with self.db:
                self.db.execute('DELETE FROM sessions WHERE expires < ?', (now,))
                self.db.execute('INSERT INTO sessions VALUES (?, ?, ?, ?)', (hashlib.sha256(token.encode()).hexdigest(), username, csrf, now + 28800))
            self.failures.pop(client_ip, None)
            return token, {'username': username, 'role': user['role'], 'employee_id': user['employee_id'], 'csrf_token': csrf}

    def session(self, token):
        with self.lock:
            row = self.db.execute('SELECT u.username,u.role,u.employee_id,s.csrf FROM sessions s JOIN users u ON u.username=s.username WHERE s.token_hash=? AND s.expires>?', (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
            if not row:
                raise HTTPException(401, detail='Please sign in again')
            return {'username': row['username'], 'role': row['role'], 'employee_id': row['employee_id'], 'csrf_token': row['csrf']}

    def logout(self, token):
        with self.lock, self.db:
            self.db.execute('DELETE FROM sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))

    def close(self):
        self.db.close()


def current_user(request: Request):
    user = request.app.state.auth.session(request.cookies.get(COOKIE_NAME, ''))
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        if not hmac.compare_digest(request.headers.get('X-CSRF-Token', ''), user['csrf_token']):
            raise HTTPException(403, detail='Invalid CSRF token. Refresh and retry.')
    return user


def require_hr(user):
    if user['role'] != 'hr':
        raise HTTPException(403, detail='HR access required')


def require_employee(user, employee_id):
    if user['role'] != 'hr' and user['employee_id'] != employee_id:
        raise HTTPException(403, detail='You can only access your own profile')
