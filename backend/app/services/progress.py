from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from ..config import AS_OF_DATE, MAX_PROFICIENCY, REPEATABLE_EVENT_IDS


def effective_skills(
    employee: dict[str, Any],
    history: Iterable[dict[str, Any]],
    events_by_id: dict[str, dict[str, Any]],
) -> dict[str, int]:
    """Apply post-review completed gains to the employee's review snapshot once per activity."""
    skills = {key: int(value) for key, value in employee.get("skills", {}).items()}
    review_date = date.fromisoformat(employee["last_review_date"])
    rows = sorted(
        (
            row
            for row in history
            if row["employee_id"] == employee["employee_id"]
            and row["status"] == "completed"
            and date.fromisoformat(row["date"]) > review_date
            and date.fromisoformat(row["date"]) <= AS_OF_DATE
        ),
        key=lambda row: (row["date"], row["record_id"]),
    )
    applied_non_repeatable: set[str] = set()
    for row in rows:
        event_id = row["event_id"]
        if event_id not in REPEATABLE_EVENT_IDS and event_id in applied_non_repeatable:
            continue
        applied_non_repeatable.add(event_id)
        event = events_by_id.get(event_id)
        if not event:
            continue
        for item in event.get("develops_skills", []):
            skill_id = item["skill_id"]
            before = skills.get(skill_id, 0)
            skills[skill_id] = min(
                MAX_PROFICIENCY,
                int(item.get("max_level", MAX_PROFICIENCY)),
                before + int(item.get("gain", 0)),
            )
    return skills


def career_progress(
    target_profile: dict[str, Any] | None,
    skills: dict[str, int],
) -> float | None:
    if not target_profile:
        return None
    required = target_profile.get("required_skills", {})
    critical = set(target_profile.get("critical_skills", []))
    if not required:
        return 100.0
    weighted_sum = 0.0
    total_weight = 0.0
    for skill_id, required_level in required.items():
        required_level = int(required_level)
        coverage = 1.0 if required_level <= 0 else min(skills.get(skill_id, 0) / required_level, 1.0)
        weight = 1.5 if skill_id in critical else 1.0
        weighted_sum += coverage * weight
        total_weight += weight
    return round(max(0.0, min(100.0, weighted_sum / total_weight * 100)), 1)
