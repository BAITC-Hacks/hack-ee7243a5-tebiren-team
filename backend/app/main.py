from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware

from .config import openai_enabled
from .data_loader import load_dataset
from .recommendation.engine import build_employee_context, event_is_eligible_for_completion, recommendations
from .schemas import (
    ActivityHistoryItem,
    CompleteRequest,
    CompleteResponse,
    EmployeeDetail,
    EmployeeListResponse,
    EmployeeSummary,
    HealthResponse,
    HRSummary,
    ImportResponse,
    RecommendationRequest,
    RecommendationsResponse,
    ResetResponse,
    SkillGap,
    Target,
    UpdatedSkill,
)
from .services.hr import build_hr_summary
from .services.import_service import parse_csv_text, parse_import
from .services.runtime_state import RuntimeState


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
state = RuntimeState(load_dataset(DATA_DIR))
app = FastAPI(title="Career Quest Backend", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _not_found(employee_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Employee {employee_id} not found")


def _target(value: dict[str, Any] | None) -> Target | None:
    if not value:
        return None
    if "role" in value and "grade" in value:
        return Target(**value)
    return Target(role=value["target_role"], grade=value["target_grade"])


def _gap_models(gaps: list[dict[str, Any]]) -> list[SkillGap]:
    return [SkillGap(**gap) for gap in gaps]


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", dataset_loaded=True, employees=len(state.employees), openai_enabled=openai_enabled())


@app.get("/api/employees", response_model=EmployeeListResponse)
def employees(search: str | None = Query(default=None), limit: int = Query(default=200, ge=1, le=500)) -> EmployeeListResponse:
    values = []
    normalized = search.casefold() if search else None
    for employee in sorted(state.employees.values(), key=lambda item: item["employee_id"]):
        if normalized and normalized not in f"{employee['employee_id']} {employee['full_name']} {employee['role']}".casefold():
            continue
        values.append(EmployeeSummary(**{key: employee[key] for key in ("employee_id", "full_name", "role", "grade")}))
        if len(values) >= limit:
            break
    return EmployeeListResponse(employees=values)


@app.get("/api/employees/{employee_id}", response_model=EmployeeDetail)
def employee_detail(employee_id: str) -> EmployeeDetail:
    try:
        context = build_employee_context(state, employee_id)
    except KeyError:
        raise _not_found(employee_id)
    history = []
    for row in sorted(context["history"], key=lambda item: (item["date"], item["record_id"]), reverse=True)[:20]:
        event = state.events_by_id[row["event_id"]]
        history.append(
            ActivityHistoryItem(
                record_id=row["record_id"],
                event_id=row["event_id"],
                title=event["title"],
                date=row["date"],
                status=row["status"],
                completion_pct=int(row["completion_pct"]),
                due_date=row["due_date"] or None,
                feedback_rating=int(row["feedback_rating"]) if row["feedback_rating"] else None,
            )
        )
    employee = context["employee"]
    profile = context["target_profile"]
    return EmployeeDetail(
        employee_id=employee["employee_id"],
        full_name=employee["full_name"],
        department=employee["department"],
        role=employee["role"],
        grade=employee["grade"],
        tenure_months=employee["tenure_months"],
        preferred_language=employee["preferred_language"],
        career_goal=_target(employee.get("career_goal")),
        target=_target(context["target"]),
        effective_skills=context["skills"],
        required_target_skills=profile.get("required_skills", {}) if profile else {},
        skill_gaps=_gap_models(context["gaps"]),
        critical_skills=profile.get("critical_skills", []) if profile else [],
        career_progress=context["progress"],
        recent_activity_history=history,
    )


@app.post("/api/employees/{employee_id}/recommendations", response_model=RecommendationsResponse)
def employee_recommendations(employee_id: str, request: RecommendationRequest | None = None) -> RecommendationsResponse:
    if not state.employee(employee_id):
        raise _not_found(employee_id)
    result = recommendations(state, employee_id, (request or RecommendationRequest()).max_recommendations)
    return RecommendationsResponse(
        employee_id=employee_id,
        target=_target(result["target"]),
        progress=result["progress"],
        skill_gaps=_gap_models(result["gaps"]),
        recommendations=result["recommendations"],
        reason=result["reason"],
    )


@app.post("/api/employees/{employee_id}/complete", response_model=CompleteResponse)
def complete(employee_id: str, request: CompleteRequest) -> CompleteResponse:
    if not state.employee(employee_id):
        raise _not_found(employee_id)
    try:
        before = build_employee_context(state, employee_id)
        eligible, reason = event_is_eligible_for_completion(state, employee_id, request.event_id)
        if not eligible:
            if reason == "event not found":
                raise HTTPException(status_code=404, detail=f"Event {request.event_id} not found")
            raise HTTPException(status_code=422, detail=reason)
        state.complete(employee_id, request.event_id)
        after = build_employee_context(state, employee_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    updated = []
    for skill_id, after_level in sorted(after["skills"].items()):
        before_level = before["skills"].get(skill_id, 0)
        if after_level != before_level:
            updated.append(UpdatedSkill(skill_id=skill_id, before=before_level, after=after_level))
    return CompleteResponse(
        success=True,
        employee_id=employee_id,
        event_id=request.event_id,
        progress_before=before["progress"],
        progress_after=after["progress"],
        updated_skills=updated,
    )


@app.get("/api/hr/summary", response_model=HRSummary)
def hr_summary() -> HRSummary:
    return HRSummary(**build_hr_summary(state))


@app.post("/api/reset", response_model=ResetResponse)
def reset() -> ResetResponse:
    state.reset()
    return ResetResponse(success=True)


async def _parse_import_request(request: Request) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        form = await request.form()
        employees_value = form.get("employees")
        history_value = form.get("activity_history") or form.get("history")
        employees = json.loads(await employees_value.read()) if hasattr(employees_value, "read") else json.loads(employees_value or "[]")
        if hasattr(history_value, "read"):
            history = parse_csv_text((await history_value.read()).decode("utf-8"))
        else:
            history = json.loads(history_value or "[]")
        return employees, history
    payload = await request.json()
    if not isinstance(payload, dict):
        raise ValueError("import body must be an object")
    return payload.get("employees", []), payload.get("activity_history", payload.get("history", []))


@app.post("/api/import", response_model=ImportResponse)
async def import_data(request: Request) -> ImportResponse:
    try:
        employees_value, history_value = await _parse_import_request(request)
        if not isinstance(employees_value, list) or not isinstance(history_value, list):
            raise ValueError("employees and activity_history must be arrays")
        new_employees, new_history, warnings = parse_import(
            employees=employees_value, history=history_value, state=state
        )
        state.add_import(new_employees, new_history)
        return ImportResponse(
            success=True,
            employees_added=len(new_employees),
            history_rows_added=len(new_history),
            warnings=warnings,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
