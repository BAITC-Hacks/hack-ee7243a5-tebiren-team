from __future__ import annotations

from copy import deepcopy
from datetime import date
from threading import RLock
from typing import Any

from ..config import AS_OF_DATE, REPEATABLE_EVENT_IDS
from ..data_loader import Dataset


class RuntimeState:
    """Mutable demo state kept separate from immutable source data."""

    def __init__(self, dataset: Dataset):
        self.dataset = dataset
        self._lock = RLock()
        self.reset()

    def reset(self) -> None:
        with getattr(self, "_lock", RLock()):
            self.employees, self.history = self.dataset.clone_runtime()

    @property
    def events_by_id(self) -> dict[str, dict[str, Any]]:
        return {event["event_id"]: event for event in self.dataset.events}

    @property
    def skills_by_id(self) -> dict[str, dict[str, Any]]:
        return {skill["skill_id"]: skill for skill in self.dataset.skills}

    @property
    def role_profiles_by_key(self) -> dict[tuple[str, str], dict[str, Any]]:
        return {(p["role"], p["grade"]): p for p in self.dataset.role_profiles}

    def employee(self, employee_id: str) -> dict[str, Any] | None:
        return self.employees.get(employee_id)

    def employee_history(self, employee_id: str) -> list[dict[str, Any]]:
        return [row for row in self.history if row["employee_id"] == employee_id]

    def add_import(self, employees: list[dict[str, Any]], history: list[dict[str, Any]]) -> None:
        with self._lock:
            for employee in employees:
                self.employees[employee["employee_id"]] = deepcopy(employee)
            self.history.extend(deepcopy(history))

    def complete(self, employee_id: str, event_id: str) -> dict[str, Any]:
        with self._lock:
            existing = [
                row
                for row in self.history
                if row["employee_id"] == employee_id
                and row["event_id"] == event_id
                and row["status"] == "completed"
            ]
            if existing and event_id not in REPEATABLE_EVENT_IDS:
                raise ValueError("event has already been completed")
            record_id = f"RUNTIME_{len(self.history) + 1:06d}"
            row = {
                "record_id": record_id,
                "employee_id": employee_id,
                "event_id": event_id,
                "date": AS_OF_DATE.isoformat(),
                "due_date": "",
                "status": "completed",
                "completion_pct": "100",
                "score": "",
                "feedback_rating": "",
                "assigned_by": "self",
            }
            self.history.append(row)
            return deepcopy(row)
