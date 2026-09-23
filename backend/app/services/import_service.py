from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any

from ..config import AS_OF_DATE, MAX_PROFICIENCY
from ..data_loader import HISTORY_COLUMNS, VALID_STATUSES, parse_date


def _validate_employee(employee: dict[str, Any], *, state: Any, incoming_ids: set[str]) -> None:
    required = {"employee_id", "full_name", "department", "role", "grade", "manager_id", "hire_date", "tenure_months", "work_format", "preferred_language", "career_goal", "skills", "last_review_date"}
    missing = required - set(employee)
    if missing:
        raise ValueError(f"employee is missing fields: {sorted(missing)}")
    employee_id = employee["employee_id"]
    if not isinstance(employee_id, str) or not employee_id:
        raise ValueError("employee_id must be a non-empty string")
    if employee_id in state.employees or employee_id in incoming_ids:
        raise ValueError(f"duplicate employee_id {employee_id}")
    if (employee["role"], employee["grade"]) not in state.role_profiles_by_key:
        raise ValueError(f"unknown role/grade for {employee_id}")
    if not isinstance(employee["skills"], dict):
        raise ValueError(f"skills must be an object for {employee_id}")
    for skill_id, level in employee["skills"].items():
        if skill_id not in state.skills_by_id or not isinstance(level, int) or not 0 <= level <= MAX_PROFICIENCY:
            raise ValueError(f"invalid skill {skill_id} for {employee_id}")
    parse_date(employee["hire_date"], field="hire_date")
    parse_date(employee["last_review_date"], field="last_review_date")
    goal = employee.get("career_goal")
    if goal and ("target_role" not in goal or "target_grade" not in goal):
        raise ValueError(f"invalid career_goal for {employee_id}")


def parse_import(
    *,
    employees: list[dict[str, Any]],
    history: list[dict[str, Any]],
    state: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    if not employees and history:
        incoming_ids: set[str] = set()
    else:
        incoming_ids = set()
    validated_employees: list[dict[str, Any]] = []
    for employee in employees:
        _validate_employee(employee, state=state, incoming_ids=incoming_ids)
        incoming_ids.add(employee["employee_id"])
        validated_employees.append(employee)
    seen_records: set[str] = set()
    existing_records = {row["record_id"] for row in state.history}
    validated_history: list[dict[str, Any]] = []
    warnings: list[str] = []
    for row in history:
        if set(row) != HISTORY_COLUMNS:
            raise ValueError("activity history has unexpected columns")
        if row["record_id"] in existing_records or row["record_id"] in seen_records:
            raise ValueError(f"duplicate record_id {row['record_id']}")
        seen_records.add(row["record_id"])
        if row["employee_id"] not in state.employees and row["employee_id"] not in incoming_ids:
            raise ValueError(f"unknown history employee {row['employee_id']}")
        if row["event_id"] not in state.events_by_id:
            raise ValueError(f"unknown history event {row['event_id']}")
        if row["status"] not in VALID_STATUSES:
            raise ValueError(f"unknown history status {row['status']}")
        parse_date(row["date"], field="history.date")
        parse_date(row["due_date"], field="history.due_date", allow_empty=True)
        if row["date"] > AS_OF_DATE.isoformat():
            warnings.append(f"history record {row['record_id']} is after the dataset snapshot date")
        validated_history.append(row)
    return validated_employees, validated_history, sorted(set(warnings))


def parse_csv_text(text: str) -> list[dict[str, Any]]:
    reader = csv.DictReader(io.StringIO(text))
    if set(reader.fieldnames or []) != HISTORY_COLUMNS:
        raise ValueError("activity_history.csv has unexpected columns")
    return [dict(row) for row in reader]
