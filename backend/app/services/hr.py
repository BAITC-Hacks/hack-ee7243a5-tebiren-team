from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from ..recommendation.engine import recommendations


def build_hr_summary(state: Any) -> dict[str, Any]:
    grade_distribution = Counter(employee["grade"] for employee in state.employees.values())
    gap_employees: dict[str, set[str]] = defaultdict(set)
    critical_employees: dict[str, set[str]] = defaultdict(set)
    closest: list[dict[str, Any]] = []
    no_recommendations = 0
    for employee_id in sorted(state.employees):
        result = recommendations(state, employee_id, max_recommendations=1, enrich_explanations=False)
        if not result["recommendations"]:
            no_recommendations += 1
        for gap in result["gaps"]:
            if gap["gap"] > 0:
                gap_employees[gap["skill_id"]].add(employee_id)
                if gap["critical"]:
                    critical_employees[gap["skill_id"]].add(employee_id)
        if result["progress"] is not None:
            closest.append({
                "employee_id": employee_id,
                "full_name": result["employee"]["full_name"],
                "progress": result["progress"],
                "target": result["target"],
            })
    closest.sort(key=lambda item: (-item["progress"], item["employee_id"]))
    status_counts = Counter(row["status"] for row in state.history)
    unique_participants = len({row["employee_id"] for row in state.history})
    total_records = len(state.history)
    participation = {
        "total_records": total_records,
        "unique_participants": unique_participants,
        "status_counts": dict(sorted(status_counts.items())),
        "completion_rate": round(status_counts.get("completed", 0) / total_records * 100, 1) if total_records else 0.0,
    }
    gaps = []
    for skill_id, employee_ids in gap_employees.items():
        gaps.append({
            "skill_id": skill_id,
            "skill_name": state.skills_by_id.get(skill_id, {}).get("name", skill_id),
            "employees": len(employee_ids),
            "critical_for_target": len(critical_employees.get(skill_id, set())),
        })
    gaps.sort(key=lambda item: (-item["employees"], -item["critical_for_target"], item["skill_id"]))
    return {
        "total_employees": len(state.employees),
        "grade_distribution": dict(sorted(grade_distribution.items())),
        "most_common_unresolved_target_gaps": gaps[:10],
        "participation": participation,
        "employees_with_no_valid_next_step": no_recommendations,
        "closest_to_target": closest[:10],
    }
