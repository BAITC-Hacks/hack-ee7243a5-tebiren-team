from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from threading import RLock
from uuid import uuid4

from ..config import AS_OF_DATE, REPEATABLE_EVENT_IDS
from ..data_loader import Dataset


class RuntimeState:
    """Single-process demo store. Source files are immutable; writes are atomic."""

    def __init__(self, dataset: Dataset, db_path: str | None = None):
        self.dataset = dataset
        self.lock = RLock()
        self._depth = 0
        self._db = None
        self.employees, self.history = dataset.clone_runtime()
        self.completion_requests = {}
        if db_path:
            if db_path != ':memory:':
                Path(db_path).parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(db_path, check_same_thread=False)
            self._db.execute('CREATE TABLE IF NOT EXISTS runtime (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
            row = self._db.execute('SELECT payload FROM runtime WHERE id=1').fetchone()
            if row:
                saved = json.loads(row[0])
                self.employees, self.history = saved['employees'], saved['history']
                self.completion_requests = saved.get('completion_requests', {})
            else:
                self._save()
        self._events = {e['event_id']: e for e in dataset.events}
        self._skills = {s['skill_id']: s for s in dataset.skills}
        self._profiles = {(p['role'], p['grade']): p for p in dataset.role_profiles}

    def _save(self):
        if self._db:
            payload = json.dumps({'employees': self.employees, 'history': self.history, 'completion_requests': self.completion_requests})
            with self._db:
                self._db.execute('INSERT OR REPLACE INTO runtime VALUES (1, ?)', (payload,))

    @contextmanager
    def transaction(self):
        with self.lock:
            outer = self._depth == 0
            previous = deepcopy((self.employees, self.history, self.completion_requests)) if outer else None
            self._depth += 1
            try:
                yield
                if outer:
                    self._save()
            except Exception:
                if outer:
                    self.employees, self.history, self.completion_requests = previous
                raise
            finally:
                self._depth -= 1

    def snapshot(self):
        with self.lock:
            result = RuntimeState(self.dataset)
            result.employees, result.history = deepcopy((self.employees, self.history))
            return result

    def reset(self):
        with self.transaction():
            self.employees, self.history = self.dataset.clone_runtime()
            self.completion_requests = {}

    def close(self):
        if self._db:
            self._db.close()

    @property
    def events_by_id(self):
        return self._events

    @property
    def skills_by_id(self):
        return self._skills

    @property
    def role_profiles_by_key(self):
        return self._profiles

    def employee(self, employee_id):
        return self.employees.get(employee_id)

    def employee_history(self, employee_id):
        return [row for row in self.history if row['employee_id'] == employee_id]

    def add_import(self, employees, history):
        with self.transaction():
            for employee in employees:
                self.employees[employee['employee_id']] = deepcopy(employee)
            self.history.extend(deepcopy(history))

    def complete(self, employee_id: str, event_id: str):
        with self.transaction():
            if event_id not in REPEATABLE_EVENT_IDS and any(
                r['employee_id'] == employee_id and r['event_id'] == event_id
                and r['status'] == 'completed' and r['date'] <= AS_OF_DATE.isoformat() for r in self.history
            ):
                raise ValueError('event has already been completed')
            row = {
                'record_id': f'RUNTIME_{uuid4().hex}', 'employee_id': employee_id, 'event_id': event_id,
                'date': AS_OF_DATE.isoformat(), 'due_date': '', 'status': 'completed', 'completion_pct': '100',
                'score': '', 'feedback_rating': '', 'assigned_by': 'self',
                'runtime_completion': True,
                'runtime_order': max((r.get('runtime_order', 0) for r in self.history), default=0) + 1,
            }
            self.history.append(row)
            return deepcopy(row)
