from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import AuthStore, COOKIE_NAME, current_user, require_employee, require_hr
from .config import AS_OF_DATE, allowed_origins, database_path, openai_enabled
from .data_loader import load_dataset
from .recommendation.engine import build_employee_context, event_is_eligible_for_completion, recommendations
from .schemas import (
    ActivityHistoryItem, CompleteRequest, CompleteResponse, EmployeeDetail, EmployeeListResponse,
    EmployeeSummary, HealthResponse, HRSummary, ImportResponse, RecommendationRequest,
    RecommendationsResponse, ResetResponse, SkillGap, Target, UpdatedSkill,
)
from .services.hr import build_hr_summary, employees_without_step
from .services.import_service import ImportValidationError, parse_csv_text, parse_import
from .services.runtime_state import RuntimeState

DATA_DIR = Path(__file__).resolve().parents[1] / 'data'
User = Annotated[dict, Depends(current_user)]


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=1024)


def _target(value):
    if not value:
        return None
    return Target(role=value.get('role', value.get('target_role')), grade=value.get('grade', value.get('target_grade')))


def create_app(db_path: str | None = None):
    path = db_path or database_path()
    runtime = RuntimeState(load_dataset(DATA_DIR), path)
    auth = AuthStore(path)
    auth.provision_env()

    @asynccontextmanager
    async def lifespan(app):
        yield
        runtime.close()
        auth.close()

    app = FastAPI(title='Career Quest Backend', version='2.0.0', lifespan=lifespan)
    app.state.runtime, app.state.auth = runtime, auth
    trusted = allowed_origins()
    app.add_middleware(CORSMiddleware, allow_origins=trusted, allow_credentials=True,
                       allow_methods=['GET', 'POST'], allow_headers=['Content-Type', 'X-CSRF-Token', 'X-Requested-With', 'Idempotency-Key'])

    @app.middleware('http')
    async def origin_guard(request, call_next):
        origin = request.headers.get('origin')
        if request.method not in ('GET', 'HEAD', 'OPTIONS') and origin and origin not in trusted:
            return JSONResponse(status_code=403, content={'detail': 'Untrusted origin'})
        response = await call_next(request)
        if request.url.path.startswith('/api'):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.post('/api/auth/login')
    def login(body: LoginRequest, request: Request, response: Response):
        if request.headers.get('X-Requested-With') != 'CareerQuest':
            raise HTTPException(403, detail='Missing login request header')
        token, user = auth.login(body.username, body.password, request.client.host if request.client else 'unknown')
        response.set_cookie(COOKIE_NAME, token, httponly=True, samesite='lax', secure=os.getenv('CQ_SECURE_COOKIES') == 'true', max_age=28800, path='/')
        return user

    @app.get('/api/auth/me')
    def me(user: User):
        return user

    @app.post('/api/auth/logout')
    def logout(request: Request, response: Response, user: User):
        auth.logout(request.cookies.get(COOKIE_NAME, ''))
        response.delete_cookie(COOKIE_NAME, path='/')
        return {'success': True}

    @app.get('/api/health', response_model=HealthResponse)
    def health():
        return HealthResponse(status='ok', dataset_loaded=True, employees=len(runtime.employees), openai_enabled=openai_enabled(), dataset_as_of=AS_OF_DATE.isoformat())

    @app.get('/api/employees', response_model=EmployeeListResponse)
    def employees(user: User, search: str = '', limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0)):
        require_hr(user)
        with runtime.lock:
            values = [e for e in sorted(runtime.employees.values(), key=lambda e: e['employee_id'])
                      if search.casefold() in f"{e['employee_id']} {e['full_name']} {e['role']}".casefold()]
            return EmployeeListResponse(employees=[EmployeeSummary(**e) for e in values[offset:offset + limit]], total=len(values), offset=offset, limit=limit)

    @app.get('/api/employees/{employee_id}', response_model=EmployeeDetail)
    def employee_detail(employee_id: str, user: User):
        require_employee(user, employee_id)
        snapshot = runtime.snapshot()
        try:
            c = build_employee_context(snapshot, employee_id)
        except KeyError:
            raise HTTPException(404, detail='Employee not found')
        history = [
            ActivityHistoryItem(record_id=r['record_id'], event_id=r['event_id'], title=snapshot.events_by_id[r['event_id']]['title'],
                                date=r['date'], status=r['status'], completion_pct=int(r['completion_pct']), due_date=r['due_date'] or None,
                                feedback_rating=int(r['feedback_rating']) if r['feedback_rating'] else None)
            for r in sorted(c['history'], key=lambda r: (r['date'], r['record_id']), reverse=True)
        ]
        e, profile = c['employee'], c['target_profile']
        return EmployeeDetail(
            employee_id=e['employee_id'], full_name=e['full_name'], department=e['department'], role=e['role'], grade=e['grade'],
            tenure_months=e['tenure_months'], preferred_language=e['preferred_language'], career_goal=_target(e.get('career_goal')),
            target=_target(c['target']), effective_skills=c['skills'], required_target_skills=profile.get('required_skills', {}) if profile else {},
            skill_gaps=[SkillGap(**g) for g in c['gaps']], critical_skills=profile.get('critical_skills', []) if profile else [],
            career_progress=c['progress'], recent_activity_history=history, dataset_as_of=AS_OF_DATE.isoformat(),
        )

    @app.post('/api/employees/{employee_id}/recommendations', response_model=RecommendationsResponse)
    def employee_recommendations(employee_id: str, user: User, body: RecommendationRequest | None = None):
        require_employee(user, employee_id)
        snapshot = runtime.snapshot()
        if not snapshot.employee(employee_id):
            raise HTTPException(404, detail='Employee not found')
        r = recommendations(snapshot, employee_id, (body or RecommendationRequest()).max_recommendations)
        return RecommendationsResponse(employee_id=employee_id, target=_target(r['target']), progress=r['progress'],
                                       skill_gaps=[SkillGap(**g) for g in r['gaps']], recommendations=r['recommendations'],
                                       reason=r['reason'], reason_code=r['reason_code'])

    @app.post('/api/employees/{employee_id}/complete', response_model=CompleteResponse)
    def complete(employee_id: str, body: CompleteRequest, request: Request, user: User):
        require_employee(user, employee_id)
        key = request.headers.get('Idempotency-Key')
        if key and len(key) > 128:
            raise HTTPException(422, detail='Idempotency key too long')
        scope = f"{user['username']}:{employee_id}:{key}" if key else None
        with runtime.transaction():
            if scope and scope in runtime.completion_requests:
                saved = runtime.completion_requests[scope]
                if saved['event_id'] != body.event_id:
                    raise HTTPException(409, detail='Idempotency key already used for another event')
                return saved
            if not runtime.employee(employee_id):
                raise HTTPException(404, detail='Employee not found')
            before = build_employee_context(runtime, employee_id)
            eligible, reason = event_is_eligible_for_completion(runtime, employee_id, body.event_id)
            if not eligible:
                raise HTTPException(404 if reason == 'event not found' else 422, detail=reason)
            runtime.complete(employee_id, body.event_id)
            after = build_employee_context(runtime, employee_id)
            response = CompleteResponse(success=True, employee_id=employee_id, event_id=body.event_id,
                                        progress_before=before['progress'], progress_after=after['progress'],
                                        updated_skills=[UpdatedSkill(skill_id=sid, skill_name=runtime.skills_by_id[sid]['name'], before=before['skills'].get(sid, 0), after=value)
                                                        for sid, value in sorted(after['skills'].items()) if value != before['skills'].get(sid, 0)])
            if scope:
                runtime.completion_requests[scope] = response.model_dump()
            return response

    @app.get('/api/hr/summary', response_model=HRSummary)
    def hr_summary(user: User):
        require_hr(user)
        return HRSummary(**build_hr_summary(runtime.snapshot()))

    @app.get('/api/hr/employees-without-next-step')
    def no_step(user: User, limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        require_hr(user)
        rows = employees_without_step(runtime.snapshot())
        return {'employees': rows[offset:offset + limit], 'total': len(rows), 'limit': limit, 'offset': offset}

    @app.post('/api/reset', response_model=ResetResponse)
    def reset(user: User):
        require_hr(user)
        runtime.reset()
        return ResetResponse(success=True)

    @app.post('/api/import', response_model=ImportResponse)
    async def import_data(request: Request, user: User):
        require_hr(user)
        try:
            employees_value, history_value = await _parse_import_request(request)
            with runtime.transaction():
                new_employees, new_history, warnings = parse_import(employees=employees_value, history=history_value, state=runtime)
                runtime.add_import(new_employees, new_history)
            return ImportResponse(success=True, employees_added=len(new_employees), history_rows_added=len(new_history),
                                  warnings=warnings, imported_employee_ids=[e['employee_id'] for e in new_employees])
        except ImportValidationError as exc:
            raise HTTPException(422, detail=exc.detail) from exc
        except (ValueError, UnicodeError) as exc:
            raise HTTPException(422, detail={'code': 'invalid_import', 'message': str(exc)}) from exc

    return app


async def _parse_import_request(request):
    async def read_upload(value):
        if hasattr(value, 'read'):
            data = await value.read(5 * 1024 * 1024 + 1)
            if len(data) > 5 * 1024 * 1024:
                raise ValueError('Each file must be at most 5 MB')
            return data.decode('utf-8-sig')
        return value or ''

    if request.headers.get('content-type', '').startswith('multipart/form-data'):
        form = await request.form()
        employees_doc = json.loads(await read_upload(form.get('employees')) or '[]')
        history_doc = await read_upload(form.get('activity_history') or form.get('history'))
        history = parse_csv_text(history_doc) if history_doc else []
    else:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError('Import body must be an object')
        employees_doc = payload.get('employees', [])
        history = payload.get('activity_history', payload.get('history', []))
    # The starter employees.json is a document with meta + employees; arrays remain supported.
    employees = employees_doc.get('employees') if isinstance(employees_doc, dict) else employees_doc
    return employees, history


app = create_app()
state = app.state.runtime
