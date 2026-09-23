from __future__ import annotations

import csv
import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .config import AS_OF_DATE, MAX_PROFICIENCY


HISTORY_COLUMNS = {
    "record_id",
    "employee_id",
    "event_id",
    "date",
    "due_date",
    "status",
    "completion_pct",
    "score",
    "feedback_rating",
    "assigned_by",
}
VALID_STATUSES = {"completed", "in_progress", "dropped", "no_show", "declined", "overdue"}


def parse_date(value: Any, *, field: str, allow_empty: bool = False) -> date | None:
    if value in (None, "") and allow_empty:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be an ISO date string")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO date string") from exc


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read {path.name}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain an object")
    return value


@dataclass(frozen=True)
class Dataset:
    meta: dict[str, Any]
    proficiency_scale: dict[str, str]
    skills: tuple[dict[str, Any], ...]
    role_profiles: tuple[dict[str, Any], ...]
    employees: tuple[dict[str, Any], ...]
    events: tuple[dict[str, Any], ...]
    history: tuple[dict[str, Any], ...]

    def clone_runtime(self) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        return (
            {item["employee_id"]: deepcopy(item) for item in self.employees},
            [deepcopy(item) for item in self.history],
        )


def _validate_dataset(
    *,
    skills_doc: dict[str, Any],
    employees_doc: dict[str, Any],
    events_doc: dict[str, Any],
    history: list[dict[str, Any]],
) -> None:
    if skills_doc.get("meta", {}).get("as_of_date") != AS_OF_DATE.isoformat():
        raise ValueError("skills.json has an unexpected snapshot date")
    if employees_doc.get("meta", {}).get("as_of_date") != AS_OF_DATE.isoformat():
        raise ValueError("employees.json has an unexpected snapshot date")
    if events_doc.get("meta", {}).get("as_of_date") != AS_OF_DATE.isoformat():
        raise ValueError("events.json has an unexpected snapshot date")

    skills = {item["skill_id"] for item in skills_doc.get("skills", [])}
    profiles = {(item["role"], item["grade"]): item for item in skills_doc.get("role_profiles", [])}
    employees = {item["employee_id"]: item for item in employees_doc.get("employees", [])}
    events = {item["event_id"]: item for item in events_doc.get("events", [])}
    if len(employees) != len(employees_doc.get("employees", [])):
        raise ValueError("employee_id values must be unique")
    if len(events) != len(events_doc.get("events", [])):
        raise ValueError("event_id values must be unique")
    if len(skills) != len(skills_doc.get("skills", [])):
        raise ValueError("skill_id values must be unique")

    for employee in employees.values():
        if (employee.get("role"), employee.get("grade")) not in profiles:
            raise ValueError(f"missing role profile for {employee['employee_id']}")
        for skill_id, level in employee.get("skills", {}).items():
            if skill_id not in skills:
                raise ValueError(f"unknown skill {skill_id} in {employee['employee_id']}")
            if not isinstance(level, int) or not 0 <= level <= MAX_PROFICIENCY:
                raise ValueError(f"invalid skill level for {employee['employee_id']}:{skill_id}")
        parse_date(employee.get("hire_date"), field="hire_date")
        parse_date(employee.get("last_review_date"), field="last_review_date")
        goal = employee.get("career_goal")
        if goal is not None and not {"target_role", "target_grade"} <= set(goal):
            raise ValueError(f"invalid career_goal for {employee['employee_id']}")

    for profile in profiles.values():
        for skill_id in profile.get("required_skills", {}):
            if skill_id not in skills:
                raise ValueError(f"unknown required skill {skill_id}")
        for skill_id in profile.get("critical_skills", []):
            if skill_id not in skills:
                raise ValueError(f"unknown critical skill {skill_id}")

    for event in events.values():
        for item in event.get("develops_skills", []):
            if item["skill_id"] not in skills:
                raise ValueError(f"unknown developed skill {item['skill_id']}")
        for skill_id in event.get("prerequisites", {}):
            if skill_id not in skills:
                raise ValueError(f"unknown prerequisite skill {skill_id}")
        for session in event.get("upcoming_sessions", []):
            parse_date(session, field=f"{event['event_id']}.upcoming_sessions")

    seen_records: set[str] = set()
    for row in history:
        if set(row) != HISTORY_COLUMNS:
            raise ValueError("activity_history.csv has unexpected columns")
        if row["record_id"] in seen_records:
            raise ValueError(f"duplicate record_id {row['record_id']}")
        seen_records.add(row["record_id"])
        if row["employee_id"] not in employees:
            raise ValueError(f"unknown history employee {row['employee_id']}")
        if row["event_id"] not in events:
            raise ValueError(f"unknown history event {row['event_id']}")
        if row["status"] not in VALID_STATUSES:
            raise ValueError(f"unknown activity status {row['status']}")
        parse_date(row["date"], field="history.date")
        parse_date(row["due_date"], field="history.due_date", allow_empty=True)


def load_dataset(data_dir: str | Path) -> Dataset:
    data_dir = Path(data_dir)
    skills_doc = _read_json(data_dir / "skills.json")
    employees_doc = _read_json(data_dir / "employees.json")
    events_doc = _read_json(data_dir / "events.json")
    history_path = data_dir / "activity_history.csv"
    with history_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or []) != HISTORY_COLUMNS:
            raise ValueError("activity_history.csv has unexpected columns")
        history = [dict(row) for row in reader]
    _validate_dataset(
        skills_doc=skills_doc,
        employees_doc=employees_doc,
        events_doc=events_doc,
        history=history,
    )
    return Dataset(
        meta=deepcopy(skills_doc["meta"]),
        proficiency_scale=deepcopy(skills_doc["proficiency_scale"]),
        skills=tuple(deepcopy(skills_doc["skills"])),
        role_profiles=tuple(deepcopy(skills_doc["role_profiles"])),
        employees=tuple(deepcopy(employees_doc["employees"])),
        events=tuple(deepcopy(events_doc["events"])),
        history=tuple(deepcopy(history)),
    )
