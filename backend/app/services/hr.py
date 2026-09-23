from collections import Counter, defaultdict

from ..config import AS_OF_DATE
from ..data_loader import VALID_STATUSES
from ..recommendation.engine import recommendations


def employees_without_step(state):
    rows = []
    for eid, employee in sorted(state.employees.items()):
        result = recommendations(state, eid, max_recommendations=1, enrich_explanations=False)
        if not result['recommendations']:
            rows.append({**{k: employee[k] for k in ('employee_id', 'full_name', 'role', 'grade')},
                         'target': result['target'], 'reason': result['reason'], 'reason_code': result['reason_code']})
    return rows


def build_hr_summary(state):
    gap_employees, critical_employees = defaultdict(set), defaultdict(set)
    closest = []
    no_steps = 0
    for eid in sorted(state.employees):
        result = recommendations(state, eid, max_recommendations=1, enrich_explanations=False)
        no_steps += not bool(result['recommendations'])
        for gap in result['gaps']:
            if gap['gap'] > 0:
                gap_employees[gap['skill_id']].add(eid)
                if gap['critical']:
                    critical_employees[gap['skill_id']].add(eid)
        if result['progress'] is not None:
            closest.append({'employee_id': eid, 'full_name': result['employee']['full_name'], 'progress': result['progress'], 'target': result['target']})
    history = [r for r in state.history if r['date'] <= AS_OF_DATE.isoformat()]
    status = Counter(r['status'] for r in history)
    per_event, participants = defaultdict(Counter), defaultdict(set)
    for row in history:
        per_event[row['event_id']][row['status']] += 1
        participants[row['event_id']].add(row['employee_id'])
    gaps = [{'skill_id': sid, 'skill_name': state.skills_by_id[sid]['name'], 'employees': len(ids),
             'critical_for_target': len(critical_employees[sid])} for sid, ids in gap_employees.items()]
    gaps.sort(key=lambda x: (-x['employees'], x['skill_id']))
    return {
        'total_employees': len(state.employees),
        'grade_distribution': dict(Counter(e['grade'] for e in state.employees.values())),
        'most_common_unresolved_target_gaps': gaps[:10],
        'participation': {
            'total_records': len(history), 'unique_participants': len({r['employee_id'] for r in history}),
            'status_counts': dict(status), 'completion_rate': round(status['completed'] / len(history) * 100, 1) if history else 0,
        },
        'employees_with_no_valid_next_step': no_steps,
        'closest_to_target': sorted(closest, key=lambda x: (-x['progress'], x['employee_id']))[:10],
        'activity_participation': [
            {'event_id': e['event_id'], 'title': e['title'], 'unique_participants': len(participants[e['event_id']]),
             **{s: per_event[e['event_id']][s] for s in sorted(VALID_STATUSES)}} for e in state.dataset.events
        ],
    }
