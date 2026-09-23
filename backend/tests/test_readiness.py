from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
import json
import time

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.data_loader import load_dataset
from app.services.runtime_state import RuntimeState
from app.services.progress import apply_gain, effective_skills
from app.recommendation.engine import recommendations, build_employee_context
from app.recommendation.explainer import OpenAIExplainer, ExplanationBatch, ExplanationItem


@pytest.fixture
def app(tmp_path, monkeypatch):
    for name in ('OPENAI_API_KEY','OPENAI_MODEL','CQ_HR_PASSWORD','CQ_EMPLOYEE_PASSWORD'):
        monkeypatch.delenv(name, raising=False)
    app = create_app(str(tmp_path / 'test.sqlite3'))
    app.state.auth.add_user('hr','test-password-hr','hr')
    app.state.auth.add_user('employee','test-password-employee','employee','E0002')
    yield app
    app.state.runtime.close()
    app.state.auth.close()


def sign_in(app, role='hr'):
    client = TestClient(app)
    result = client.post('/api/auth/login', json={'username':role,'password':'test-password-'+role}, headers={'X-Requested-With':'CareerQuest'})
    assert result.status_code == 200
    client.headers['X-CSRF-Token'] = result.json()['csrf_token']
    return client


def test_access_csrf_and_logout(app):
    anonymous = TestClient(app)
    assert anonymous.get('/api/employees/E0002').status_code == 401
    assert anonymous.get('/api/health').status_code == 200
    c = sign_in(app,'employee')
    assert c.get('/api/employees/E0002').status_code == 200
    for url in ('/api/employees','/api/employees/E0001','/api/hr/summary','/api/hr/employees-without-next-step'):
        assert c.get(url).status_code == 403
    for url, body in [('/api/import',{}),('/api/reset',{}),('/api/employees/E0001/complete',{'event_id':'EV_005'})]:
        assert c.post(url,json=body).status_code == 403
    assert c.post('/api/employees/E0002/recommendations',headers={'X-CSRF-Token':'wrong'}).status_code == 403
    assert c.post('/api/auth/logout').status_code == 200
    assert c.get('/api/auth/me').status_code == 401


def test_login_origin_and_cookie(app):
    c = TestClient(app)
    body={'username':'hr','password':'test-password-hr'}
    assert c.post('/api/auth/login',json=body).status_code==403
    assert c.post('/api/auth/login',json=body,headers={'Origin':'https://evil.example','X-Requested-With':'CareerQuest'}).status_code==403
    response=c.post('/api/auth/login',json=body,headers={'X-Requested-With':'CareerQuest'})
    assert 'HttpOnly' in response.headers['set-cookie'] and 'SameSite=lax' in response.headers['set-cookie']
    assert c.post('/api/reset').status_code==403


def test_import_wrapped_bom_and_pagination(app):
    c=sign_in(app)
    e=deepcopy(app.state.runtime.employees['E0002']); e['employee_id']='E9001'
    payload=('\ufeff'+json.dumps({'meta':{},'employees':[e]})).encode('utf-8')
    r=c.post('/api/import',files={'employees':('employees.json',payload,'application/json')})
    assert r.status_code==200, r.text
    assert r.json()['imported_employee_ids']==['E9001']
    page=c.get('/api/employees?offset=200&limit=30').json()
    assert page['total']==201 and page['employees'][0]['employee_id']=='E9001'
    assert c.get('/api/employees?search=E9001').json()['total']==1
    assert c.get('/api/employees/E9001').status_code==200
    assert c.post('/api/import',json={'employees':[e]}).status_code==422
    assert len(app.state.runtime.employees)==201


@pytest.mark.parametrize('bad', [
    {'skills':{'SK_PYTHON':True}}, {'tenure_months':-1}, {'last_review_date':'2030-01-01'},
    {'career_goal':{'target_role':'Unknown','target_grade':'Senior'}}, {'full_name':None},
])
def test_import_validation_atomic(app,bad):
    c=sign_in(app)
    good=deepcopy(app.state.runtime.employees['E0002']); good['employee_id']='E9001'
    broken=deepcopy(good);broken['employee_id']='E9002';broken.update(bad)
    r=c.post('/api/import',json={'employees':[good,broken]})
    assert r.status_code==422 and r.json()['detail']['row']==2
    assert 'E9001' not in app.state.runtime.employees


def test_hr_rows_and_totals(app):
    c=sign_in(app)
    summary=c.get('/api/hr/summary').json()
    rows=c.get('/api/hr/employees-without-next-step?limit=100').json()
    assert rows['total']==summary['employees_with_no_valid_next_step']
    assert len(rows['employees'])==rows['total']
    assert all(r['reason_code'] and r['reason'] for r in rows['employees'])
    activities=summary['activity_participation']
    assert len(activities)==40
    statuses=['completed','in_progress','dropped','no_show','declined','overdue']
    assert sum(sum(a[s] for s in statuses) for a in activities)==summary['participation']['total_records']
    for s in statuses:
        assert sum(a[s] for a in activities)==summary['participation']['status_counts'].get(s,0)


def test_persistence_idempotency_and_reset(app,tmp_path):
    c=sign_in(app)
    eid='E0002'
    rec=c.post(f'/api/employees/{eid}/recommendations').json()['recommendations'][0]
    count=len(app.state.runtime.history)
    r=c.post(f'/api/employees/{eid}/complete',json={'event_id':rec['event_id']},headers={'Idempotency-Key':'same-request'})
    assert r.status_code==200, r.text
    assert r.json()['progress_after']>=r.json()['progress_before']
    again=c.post(f'/api/employees/{eid}/complete',json={'event_id':rec['event_id']},headers={'Idempotency-Key':'same-request'})
    assert again.json()==r.json() and len(app.state.runtime.history)==count+1
    reopened=RuntimeState(app.state.runtime.dataset,str(tmp_path/'test.sqlite3'))
    assert reopened.history==app.state.runtime.history
    assert reopened.completion_requests==app.state.runtime.completion_requests
    reopened.close()
    assert c.post('/api/reset').status_code==200
    assert len(app.state.runtime.history)==2743


def test_concurrent_complete(app):
    c=sign_in(app)
    rec=c.post('/api/employees/E0002/recommendations').json()['recommendations'][0]
    count=len(app.state.runtime.history)
    def send(_):
        return c.post('/api/employees/E0002/complete',json={'event_id':rec['event_id']},headers={'Idempotency-Key':'concurrent'}).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(send,range(2)))
    assert results[0]==results[1] and len(app.state.runtime.history)==count+1


@pytest.mark.parametrize('before,gain,cap,expected',[(4,1,3,4),(5,1,4,5),(2,2,3,3),(4,3,5,5),(0,0,3,0)])
def test_growth_caps(before,gain,cap,expected):
    assert apply_gain(before,gain,cap)==expected


def test_all_profiles_monotonic_and_prediction(data_dir):
    ds=load_dataset(data_dir); state=RuntimeState(ds)
    checked=0
    for eid in state.employees:
        result=recommendations(state,eid,enrich_explanations=False)
        for rec in result['recommendations']:
            trial=RuntimeState(ds); before=build_employee_context(trial,eid)
            trial.complete(eid,rec['event_id']); after=build_employee_context(trial,eid)
            assert all(after['skills'].get(s,0)>=v for s,v in before['skills'].items()),(eid,rec['event_id'])
            assert after['progress']>=before['progress']
            assert all(after['skills'][i['skill_id']]==i['after_if_completed'] for i in rec['skill_impacts'])
            assert len({f['factor'] for f in rec['evidence']})>=3
            checked+=1
    assert checked>200


def candidates(data_dir):
    state=RuntimeState(load_dataset(data_dir))
    rec=recommendations(state,'E0002',enrich_explanations=False)['recommendations'][0]
    return [{'event_id':rec['event_id'],'evidence':rec['evidence'],'impacts':rec['skill_impacts']}]


@pytest.mark.parametrize('error',[TimeoutError,ValueError,PermissionError])
def test_provider_errors_fallback(data_dir,monkeypatch,error):
    monkeypatch.setenv('OPENAI_API_KEY','fake');monkeypatch.setenv('OPENAI_MODEL','fake')
    monkeypatch.setattr(OpenAIExplainer,'_request',lambda *a: (_ for _ in ()).throw(error()))
    assert OpenAIExplainer().explain(candidates(data_dir))=={}


def test_provider_deadline(data_dir,monkeypatch):
    from app.recommendation import explainer
    monkeypatch.setenv('OPENAI_API_KEY','fake');monkeypatch.setenv('OPENAI_MODEL','fake')
    monkeypatch.setattr(explainer,'EXPLANATION_BUDGET_SECONDS',0.05)
    monkeypatch.setattr(OpenAIExplainer,'_request',lambda *a:time.sleep(0.2))
    start=time.monotonic()
    assert OpenAIExplainer().explain(candidates(data_dir))=={}
    assert time.monotonic()-start<0.15


def test_grounded_ai_and_invalid_facts(data_dir,monkeypatch):
    monkeypatch.setenv('OPENAI_API_KEY','fake');monkeypatch.setenv('OPENAI_MODEL','fake')
    cs=candidates(data_dir); eid=cs[0]['event_id']
    batch=ExplanationBatch(explanations=[ExplanationItem(event_id=eid,fact_ids=['current','target','history'],emphasis='target')])
    monkeypatch.setattr(OpenAIExplainer,'_request',lambda *a:batch)
    result=OpenAIExplainer().explain(cs)
    assert result[eid]['explanation']
    batch.explanations[0].fact_ids=['current','fiction','history']
    assert OpenAIExplainer().explain(cs)=={}


def test_no_history_and_no_target(data_dir):
    state=RuntimeState(load_dataset(data_dir));state.history=[]
    r=recommendations(state,'E0002',enrich_explanations=False)
    assert all('No participation history' in rec['reasons'][-1] for rec in r['recommendations'])
    e=next(e for e in state.employees.values() if e['grade']=='Lead' and e['career_goal'] is None)
    assert recommendations(state,e['employee_id'],enrich_explanations=False)['reason_code']=='no_target'


@pytest.mark.parametrize('status', [401, 429])
def test_sdk_http_failures_are_bounded_fallback(data_dir, monkeypatch, status):
    import httpx
    import openai
    original = openai.OpenAI
    calls = []
    def respond(request):
        calls.append(request)
        return httpx.Response(status, json={'error': {'message': 'test failure', 'type': 'test_error'}})
    monkeypatch.setenv('OPENAI_API_KEY', 'fake-key-for-mocked-transport')
    monkeypatch.setenv('OPENAI_MODEL', 'test-model')
    monkeypatch.setattr(openai, 'OpenAI', lambda **kw: original(**kw, http_client=httpx.Client(transport=httpx.MockTransport(respond))))
    start = time.monotonic()
    assert OpenAIExplainer().explain(candidates(data_dir)) == {}
    assert len(calls) == 1  # No SDK retries.
    assert time.monotonic() - start < 2


def test_jury_files_and_restart(app, tmp_path):
    c = sign_in(app)
    examples = Path(__file__).resolve().parents[2] / 'examples' / 'jury'
    with (examples / 'employees.json').open('rb') as employees, (examples / 'activity_history.csv').open('rb') as history:
        response = c.post('/api/import', files={'employees': employees, 'history': history})
    assert response.status_code == 200, response.text
    assert response.json()['imported_employee_ids'] == ['E9001', 'E9002', 'E9003']
    result = c.post('/api/employees/E9001/recommendations').json()
    assert any('3 missed' in reason for rec in result['recommendations'] for reason in rec['reasons'])
    assert any(i['skill_name'] == 'System Design' and i['critical'] for rec in result['recommendations'] for i in rec['skill_impacts'])
    other = c.post('/api/employees/E9002/recommendations').json()
    assert other['target']['role'] != app.state.runtime.employee('E9002')['role']
    assert all('No participation history' in rec['reasons'][-1] for rec in other['recommendations'])
    assert c.post('/api/employees/E9003/recommendations').json()['reason_code'] == 'no_target'
    reopened = RuntimeState(app.state.runtime.dataset, str(tmp_path / 'test.sqlite3'))
    assert reopened.employee('E9001') == app.state.runtime.employee('E9001')
    assert len(reopened.employee_history('E9001')) == 3
    reopened.close()


def test_csv_error_rolls_back_both_files(app):
    c = sign_in(app)
    employee = deepcopy(app.state.runtime.employee('E0002')); employee['employee_id'] = 'E9010'
    row = deepcopy(app.state.runtime.history[0])
    row.update(record_id='JURY_BAD', employee_id='E9010', event_id='UNKNOWN')
    response = c.post('/api/import', json={'employees': [employee], 'history': [row]})
    assert response.status_code == 422
    assert response.json()['detail']['file'] == 'activity_history.csv'
    assert 'E9010' not in app.state.runtime.employees


def test_storage_failure_rolls_back(app, monkeypatch):
    runtime = app.state.runtime
    before = deepcopy((runtime.employees, runtime.history, runtime.completion_requests))
    def fail():
        raise OSError('simulated write failure')
    monkeypatch.setattr(runtime, '_save', fail)
    with pytest.raises(OSError):
        runtime.complete('E0002', 'EV_005')
    assert (runtime.employees, runtime.history, runtime.completion_requests) == before


def test_future_history_does_not_block_current_completion(app):
    c = sign_in(app)
    row = deepcopy(app.state.runtime.history[0])
    row.update(record_id='FUTURE_TEST', employee_id='E0002', event_id='EV_005',
               date='2027-01-01', status='completed', completion_pct='100')
    imported = c.post('/api/import', json={'history': [row]})
    assert imported.status_code == 200 and imported.json()['warnings']
    result = c.post('/api/employees/E0002/recommendations').json()
    assert 'EV_005' in [r['event_id'] for r in result['recommendations']]
    assert c.post('/api/employees/E0002/complete', json={'event_id': 'EV_005'}).status_code == 200


def test_same_snapshot_review_and_repeatable_idempotency(app):
    from app.config import AS_OF_DATE
    c = sign_in(app)
    employee = deepcopy(app.state.runtime.employee('E0002'))
    employee.update(employee_id='E9011', last_review_date=AS_OF_DATE.isoformat())
    assert c.post('/api/import', json={'employees': [employee]}).status_code == 200
    first = c.post('/api/employees/E9011/complete', json={'event_id': 'EV_005'})
    assert first.status_code == 200 and first.json()['updated_skills']
    initial = len(app.state.runtime.history)
    for _ in range(2):
        response = c.post('/api/employees/E9011/complete', json={'event_id': 'EV_036'}, headers={'Idempotency-Key': 'repeatable'})
        assert response.status_code == 200, response.text
    assert len(app.state.runtime.history) == initial + 1
    conflict = c.post('/api/employees/E9011/complete', json={'event_id': 'EV_007'}, headers={'Idempotency-Key': 'repeatable'})
    assert conflict.status_code == 409


def test_passwords_hashed_and_session_persists(app, tmp_path):
    from app.auth import AuthStore, COOKIE_NAME
    c = sign_in(app)
    row = app.state.auth.db.execute("SELECT * FROM users WHERE username='hr'").fetchone()
    assert row['password_hash'] != 'test-password-hr' and len(row['salt']) == 32
    reopened = AuthStore(str(tmp_path / 'test.sqlite3'))
    assert reopened.session(c.cookies[COOKIE_NAME])['role'] == 'hr'
    reopened.close()


def test_same_day_growth_uses_completion_order():
    employee = {'employee_id': 'E1', 'last_review_date': '2026-09-30', 'skills': {'S1': 2}}
    events = {
        'LOW': {'develops_skills': [{'skill_id': 'S1', 'gain': 1, 'max_level': 3}]},
        'HIGH': {'develops_skills': [{'skill_id': 'S1', 'gain': 1, 'max_level': 5}]},
    }
    rows = [
        {'employee_id': 'E1', 'record_id': 'Z', 'event_id': 'LOW', 'status': 'completed', 'date': '2026-10-01', 'runtime_completion': True, 'runtime_order': 1},
        {'employee_id': 'E1', 'record_id': 'A', 'event_id': 'HIGH', 'status': 'completed', 'date': '2026-10-01', 'runtime_completion': True, 'runtime_order': 2},
    ]
    assert effective_skills(employee, rows[:1], events)['S1'] == 3
    assert effective_skills(employee, rows, events)['S1'] == 4


def test_local_key_file_is_opt_in_and_empty_key_disables_it(tmp_path, monkeypatch):
    from app.config import openai_settings
    key_file = tmp_path / 'test-key.txt'
    key_file.write_text('fake-test-key', encoding='utf-8')
    monkeypatch.setenv('OPENAI_API_KEY_FILE', str(key_file))
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    monkeypatch.setenv('OPENAI_MODEL', 'test-model')
    assert openai_settings() == ('fake-test-key', 'test-model')
    monkeypatch.setenv('OPENAI_API_KEY', '')
    assert openai_settings()[0] is None


@pytest.mark.parametrize('employee_id,event_id', [('E0070', 'EV_008'), ('E0014', 'EV_037'), ('E0014', 'EV_038')])
def test_original_skill_drop_regressions(data_dir, employee_id, event_id):
    runtime = RuntimeState(load_dataset(data_dir))
    before = build_employee_context(runtime, employee_id)
    runtime.complete(employee_id, event_id)
    after = build_employee_context(runtime, employee_id)
    assert all(after['skills'].get(s, 0) >= level for s, level in before['skills'].items())
    assert after['progress'] >= before['progress']
