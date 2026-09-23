"""Read-only achievements derived from the existing participation history."""
from ..config import AS_OF_DATE


def development_summary(state, employee_id: str) -> dict[str, int]:
    completed = {
        row['event_id']
        for row in state.employee_history(employee_id)
        if row['status'] == 'completed'
        and row['date'] <= AS_OF_DATE.isoformat()
        and (event := state.events_by_id.get(row['event_id'])) is not None
        and event.get('mandatory') is False
    }
    return {'completed_unique_activities': len(completed)}
