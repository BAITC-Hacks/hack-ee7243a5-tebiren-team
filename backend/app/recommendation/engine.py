from __future__ import annotations

from datetime import date
from typing import Any

from ..config import AS_OF_DATE, GRADE_ORDER, REPEATABLE_EVENT_IDS
from ..services.progress import career_progress, effective_skills
from .explainer import OpenAIExplainer, deterministic_reasons
from .scoring import CandidateScore, score_event


def resolve_target(employee: dict[str, Any], profiles: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any] | None:
    goal = employee.get("career_goal")
    if goal:
        return {"role": goal["target_role"], "grade": goal["target_grade"]}
    try:
        next_grade = GRADE_ORDER[GRADE_ORDER.index(employee["grade"]) + 1]
    except (ValueError, IndexError):
        return None
    if (employee["role"], next_grade) not in profiles:
        return None
    return {"role": employee["role"], "grade": next_grade}


def skill_gaps(
    target_profile: dict[str, Any] | None,
    skills: dict[str, int],
    skill_catalog: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    if not target_profile:
        return []
    critical = set(target_profile.get("critical_skills", []))
    result = []
    for skill_id, required in target_profile.get("required_skills", {}).items():
        current = skills.get(skill_id, 0)
        result.append(
            {
                "skill_id": skill_id,
                "skill_name": skill_catalog.get(skill_id, {}).get("name", skill_id),
                "current": current,
                "required": int(required),
                "gap": max(int(required) - current, 0),
                "critical": skill_id in critical,
            }
        )
    return sorted(result, key=lambda item: (-item["gap"], not item["critical"], item["skill_id"]))


def _event_is_eligible(
    employee: dict[str, Any],
    event: dict[str, Any],
    skills: dict[str, int],
    history: list[dict[str, Any]],
    *,
    for_recommendation: bool = True,
) -> tuple[bool, str | None]:
    if event.get("target_roles") and employee["role"] not in event["target_roles"]:
        return False, "event is not for the employee's current role"
    if event.get("target_grades") and employee["grade"] not in event["target_grades"]:
        return False, "event is not for the employee's current grade"
    for skill_id, minimum in event.get("prerequisites", {}).items():
        if skills.get(skill_id, 0) < int(minimum):
            return False, f"prerequisite {skill_id} is not met"
    if event.get("upcoming_sessions"):
        if not any(date.fromisoformat(day) >= AS_OF_DATE for day in event["upcoming_sessions"]):
            return False, "no future session is available"
    if for_recommendation and event.get("mandatory"):
        return False, "mandatory HR activity is not a personalized recommendation"
    matching = [row for row in history if row["event_id"] == event["event_id"]]
    if any(row["status"] == "in_progress" for row in matching):
        return False, "event is already in progress"
    if any(row["status"] == "completed" for row in matching) and event["event_id"] not in REPEATABLE_EVENT_IDS:
        return False, "event was already completed"
    return True, None


def build_employee_context(state: Any, employee_id: str) -> dict[str, Any]:
    employee = state.employee(employee_id)
    if not employee:
        raise KeyError(employee_id)
    profiles = state.role_profiles_by_key
    target = resolve_target(employee, profiles)
    target_profile = profiles.get((target["role"], target["grade"])) if target else None
    skills = effective_skills(employee, state.employee_history(employee_id), state.events_by_id)
    gaps = skill_gaps(target_profile, skills, state.skills_by_id)
    return {
        "employee": employee,
        "target": target,
        "target_profile": target_profile,
        "skills": skills,
        "gaps": gaps,
        "progress": career_progress(target_profile, skills),
        "history": state.employee_history(employee_id),
    }


def recommendations(
    state: Any,
    employee_id: str,
    max_recommendations: int = 3,
    *,
    enrich_explanations: bool = True,
) -> dict[str, Any]:
    context = build_employee_context(state, employee_id)
    candidates: list[CandidateScore] = []
    target_gap_ids = {gap["skill_id"] for gap in context["gaps"] if gap["gap"] > 0}
    if not context["target"]:
        return {**context, "recommendations": [], "reason": "No promotion target is defined for this employee"}
    if not target_gap_ids:
        return {**context, "recommendations": [], "reason": "The employee currently meets all target skill requirements"}
    for event in state.dataset.events:
        eligible, _ = _event_is_eligible(
            context["employee"], event, context["skills"], context["history"], for_recommendation=True
        )
        if not eligible:
            continue
        candidate = score_event(
            event,
            skills=context["skills"],
            skill_gaps=context["gaps"],
            history=context["history"],
            events_by_id=state.events_by_id,
        )
        if not candidate.impacts:
            continue
        candidates.append(candidate)
    candidates.sort(key=lambda item: (-item.score, item.event["event_id"]))
    selected = candidates[:max_recommendations]
    enriched_input: list[dict[str, Any]] = []
    rendered: list[dict[str, Any]] = []
    for rank, candidate in enumerate(selected, start=1):
        event = candidate.event
        impacts = []
        for impact in candidate.impacts:
            impacts.append({
                **impact,
                "skill_name": state.skills_by_id.get(impact["skill_id"], {}).get("name", impact["skill_id"]),
            })
        completed_like = [row for row in context["history"] if row["event_id"] == event["event_id"] and row["status"] == "completed"]
        history_note = None
        if completed_like:
            history_note = "The employee has completed a related activity before, so this is a repeatable next step"
        elif any(row["status"] == "completed" for row in context["history"]):
            history_note = "The employee's activity history includes successful completions"
        target_note = f"The activity is eligible for the current {context['employee']['role']} {context['employee']['grade']}"
        item = {
            "rank": rank,
            "event_id": event["event_id"],
            "title": event["title"],
            "score": candidate.score,
            "score_breakdown": candidate.breakdown,
            "reasons": deterministic_reasons({"impacts": impacts, "history_note": history_note, "target_note": target_note}),
            "explanation": None,
            "skill_impacts": [
                {
                    "skill_id": impact["skill_id"],
                    "skill_name": impact["skill_name"],
                    "before": impact["before"],
                    "after_if_completed": impact["after_if_completed"],
                    "required": impact["required"],
                    "critical": impact["critical"],
                }
                for impact in impacts
            ],
            "explanation_source": "deterministic",
        }
        rendered.append(item)
        enriched_input.append({
            "event_id": event["event_id"],
            "title": event["title"],
            "target": context["target"],
            "impacts": impacts,
            "score_breakdown": candidate.breakdown,
            "history_note": history_note,
        })
    if enrich_explanations:
        try:
            llm = OpenAIExplainer().explain(enriched_input)
        except Exception:
            llm = {}
    else:
        llm = {}
    for item in rendered:
        if item["event_id"] in llm:
            item["explanation"] = llm[item["event_id"]]["explanation"]
            item["reasons"] = llm[item["event_id"]]["reasons"] or item["reasons"]
            item["explanation_source"] = "openai"
    return {**context, "recommendations": rendered, "reason": None if rendered else "No eligible development activity addresses the unresolved target gaps"}


def event_is_eligible_for_completion(state: Any, employee_id: str, event_id: str) -> tuple[bool, str | None]:
    context = build_employee_context(state, employee_id)
    event = state.events_by_id.get(event_id)
    if not event:
        return False, "event not found"
    return _event_is_eligible(
        context["employee"], event, context["skills"], context["history"], for_recommendation=False
    )
