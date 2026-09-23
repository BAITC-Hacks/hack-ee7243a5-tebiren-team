from __future__ import annotations

import csv
import io
from typing import Any

from ..config import AS_OF_DATE, MAX_PROFICIENCY
from ..data_loader import HISTORY_COLUMNS, VALID_STATUSES, parse_date


class ImportValidationError(ValueError):
    def __init__(self, message, *, file=None, row=None, field=None):
        super().__init__(message)
        self.detail = {'code': 'invalid_import', 'message': message, 'file': file, 'row': row, 'field': field}


def _validate_employee(employee, *, state, incoming_ids):
    if not isinstance(employee, dict):
        raise ValueError('Employee must be an object')
    required = {'employee_id', 'full_name', 'department', 'role', 'grade', 'manager_id', 'hire_date', 'tenure_months', 'work_format', 'preferred_language', 'career_goal', 'skills', 'last_review_date'}
    missing = required - set(employee)
    if missing:
        raise ValueError(f'Missing fields: {sorted(missing)}')
    for name in ('employee_id', 'full_name', 'department', 'role', 'grade', 'work_format', 'preferred_language'):
        if not isinstance(employee[name], str) or not employee[name].strip():
            raise ValueError(f'{name} must be a non-empty string')
    if employee['manager_id'] is not None and not isinstance(employee['manager_id'], str):
        raise ValueError('manager_id must be a string or null')
    eid = employee['employee_id']
    if eid in state.employees or eid in incoming_ids:
        raise ValueError(f'Duplicate employee_id {eid}')
    if (employee['role'], employee['grade']) not in state.role_profiles_by_key:
        raise ValueError('Unknown role/grade')
    if type(employee['tenure_months']) is not int or employee['tenure_months'] < 0:
        raise ValueError('tenure_months must be a non-negative integer')
    if not isinstance(employee['skills'], dict):
        raise ValueError('skills must be an object')
    for sid, level in employee['skills'].items():
        if sid not in state.skills_by_id or type(level) is not int or not 0 <= level <= MAX_PROFICIENCY:
            raise ValueError(f'Invalid skill or level: {sid}')
    hire = parse_date(employee['hire_date'], field='hire_date')
    review = parse_date(employee['last_review_date'], field='last_review_date')
    if hire > review or review > AS_OF_DATE:
        raise ValueError('Dates must satisfy hire_date <= last_review_date <= snapshot date')
    goal = employee['career_goal']
    if goal is not None:
        if not isinstance(goal, dict) or not isinstance(goal.get('target_role'), str) or not isinstance(goal.get('target_grade'), str):
            raise ValueError('Invalid career_goal')
        if (goal['target_role'], goal['target_grade']) not in state.role_profiles_by_key:
            raise ValueError('Unknown target role/grade')


def parse_import(*, employees, history, state):
    if not isinstance(employees, list) or not isinstance(history, list):
        raise ImportValidationError('employees and activity_history must be arrays')
    if not employees and not history:
        raise ImportValidationError('Provide at least one employee or history row')
    incoming_ids = set()
    for number, employee in enumerate(employees, 1):
        try:
            _validate_employee(employee, state=state, incoming_ids=incoming_ids)
            incoming_ids.add(employee['employee_id'])
        except (ValueError, TypeError) as exc:
            raise ImportValidationError(str(exc), file='employees.json', row=number) from exc
    existing_records = {r['record_id'] for r in state.history}
    seen_records = set()
    warnings = []
    for number, row in enumerate(history, 2):
        try:
            if not isinstance(row, dict) or set(row) != HISTORY_COLUMNS:
                raise ValueError('Activity history has unexpected columns')
            if not isinstance(row['record_id'], str) or not row['record_id'].strip():
                raise ValueError('record_id must be a non-empty string')
            if row['record_id'] in existing_records or row['record_id'] in seen_records:
                raise ValueError(f'Duplicate record_id {row["record_id"]}')
            if row['employee_id'] not in state.employees and row['employee_id'] not in incoming_ids:
                raise ValueError(f'Unknown employee {row["employee_id"]}')
            if row['event_id'] not in state.events_by_id:
                raise ValueError(f'Unknown event {row["event_id"]}')
            if row['status'] not in VALID_STATUSES:
                raise ValueError(f'Unknown status {row["status"]}')
            parse_date(row['date'], field='date')
            parse_date(row['due_date'], field='due_date', allow_empty=True)
            for field, maximum, minimum in [('completion_pct', 100, 0), ('score', 100, 0), ('feedback_rating', 5, 1)]:
                value = row[field]
                if field != 'completion_pct' and value in ('', None):
                    continue
                if isinstance(value, bool) or not str(value).isdigit() or not minimum <= int(value) <= maximum:
                    raise ValueError(f'{field} must be an integer in {minimum}..{maximum}')
            if not isinstance(row['assigned_by'], str):
                raise ValueError('assigned_by must be a string')
            if row['date'] > AS_OF_DATE.isoformat():
                warnings.append(f'Row {number}: future history is excluded from current skills and recommendations')
            seen_records.add(row['record_id'])
        except (ValueError, TypeError) as exc:
            raise ImportValidationError(str(exc), file='activity_history.csv', row=number) from exc
    return employees, history, sorted(set(warnings))


def parse_csv_text(text: str):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if set(reader.fieldnames or []) != HISTORY_COLUMNS or len(reader.fieldnames or []) != len(HISTORY_COLUMNS):
        raise ImportValidationError('Unexpected or duplicate history columns', file='activity_history.csv', row=1)
    return list(reader)
