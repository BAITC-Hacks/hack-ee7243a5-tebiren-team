from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.services.development import development_summary
from app.services.runtime_state import RuntimeState
from app.recommendation.engine import recommendations
from .test_readiness import app, sign_in


def mini_state(rows):
    events = {eid: {'mandatory': False} for eid in ('A', 'B', 'C')}
    events.update(HR={'mandatory': True}, UNKNOWN_FLAG={})
    return SimpleNamespace(events_by_id=events, employee_history=lambda eid: [r for r in rows if r.get('employee_id', 'E1') == eid])


def row(event='A', status='completed', day='2026-09-01', **extra):
    return {'event_id': event, 'status': status, 'date': day, **extra}


@pytest.mark.parametrize('count', range(4))
def test_zero_through_three_unique_activities(count):
    state = mini_state([row(eid) for eid in ('A', 'B', 'C')[:count]])
    assert development_summary(state, 'E1') == {'completed_unique_activities': count}


def test_only_distinct_known_voluntary_completed_history_counts():
    rows = [row('A'), row('A'), row('A'), row('HR'), row('missing'), row('UNKNOWN_FLAG'),
            row('B', day='2026-10-02'), row('C', employee_id='E2')]
    rows.extend(row('B', status=status) for status in ('no_show', 'declined', 'dropped', 'in_progress', 'overdue'))
    assert development_summary(mini_state(rows), 'E1')['completed_unique_activities'] == 1
    # Historical completions and the snapshot day both count; review dates don't
    # remove recognition of previous voluntary learning.
    assert development_summary(mini_state([row('A', day='2024-01-01'), row('B', day='2026-10-01')]), 'E1')['completed_unique_activities'] == 2


def test_profile_completion_replay_restart_import_and_reset(app, tmp_path):
    c = sign_in(app)
    original = c.get('/api/employees/E0002').json()['development_summary']
    assert original['completed_unique_activities'] > 0
    employee = deepcopy(app.state.runtime.employee('E0002'))
    employee['employee_id'] = 'E9012'
    imported = deepcopy(app.state.runtime.history[0])
    imported.update(record_id='ACHIEVEMENT_HISTORY', employee_id='E9012', event_id='EV_036',
                    status='completed', date='2024-01-01', completion_pct='100')
    assert c.post('/api/import', json={'employees': [employee], 'history': [imported]}).status_code == 200
    assert c.get('/api/employees/E9012').json()['development_summary']['completed_unique_activities'] == 1
    used = {'EV_036'}
    saved = None
    for count in (2, 3):
        recs = c.post('/api/employees/E9012/recommendations').json()['recommendations']
        event_id = next(rec['event_id'] for rec in recs if rec['event_id'] not in used)
        used.add(event_id)
        response = c.post('/api/employees/E9012/complete', json={'event_id': event_id}, headers={'Idempotency-Key': f'badge-{count}'})
        assert response.status_code == 200, response.text
        assert response.json()['development_summary']['completed_unique_activities'] == count
        if count == 2:
            saved = response.json()
    before = len(app.state.runtime.history)
    replay = c.post('/api/employees/E9012/complete', json={'event_id': saved['event_id']}, headers={'Idempotency-Key': 'badge-2'})
    assert replay.json() == saved
    assert len(app.state.runtime.history) == before
    assert c.get('/api/employees/E9012').json()['development_summary']['completed_unique_activities'] == 3
    reopened = RuntimeState(app.state.runtime.dataset, str(tmp_path / 'test.sqlite3'))
    assert development_summary(reopened, 'E9012')['completed_unique_activities'] == 3
    reopened.close()
    assert c.post('/api/reset').status_code == 200
    assert c.get('/api/employees/E9012').status_code == 404
    assert c.get('/api/employees/E0002').json()['development_summary'] == original


def test_legacy_completion_response_remains_compatible(app):
    c = sign_in(app)
    response = c.post('/api/employees/E0002/complete', json={'event_id': 'EV_005'}, headers={'Idempotency-Key': 'legacy'})
    assert response.status_code == 200
    with app.state.runtime.transaction():
        app.state.runtime.completion_requests['hr:E0002:legacy'].pop('development_summary')
    before = len(app.state.runtime.history)
    again = c.post('/api/employees/E0002/complete', json={'event_id': 'EV_005'}, headers={'Idempotency-Key': 'legacy'})
    assert again.status_code == 200 and again.json()['development_summary'] is None
    assert len(app.state.runtime.history) == before
    assert c.get('/api/employees/E0002').json()['development_summary']['completed_unique_activities'] > 0


def test_summary_does_not_modify_skills_progress_or_ranking(app):
    runtime = app.state.runtime
    before = recommendations(runtime, 'E0002', enrich_explanations=False)
    history = deepcopy(runtime.history)
    development_summary(runtime, 'E0002')
    assert runtime.history == history
    assert recommendations(runtime, 'E0002', enrich_explanations=False) == before
    c = sign_in(app, 'employee')
    assert 'development_summary' in c.get('/api/employees/E0002').json()
    assert c.get('/api/employees/E0001').status_code == 403
