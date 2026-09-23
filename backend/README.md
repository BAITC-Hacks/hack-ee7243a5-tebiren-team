# Career Quest backend

This backend loads the supplied Career Quest JSON/CSV snapshot, resolves each employee's promotion target, applies valid post-review activity gains, calculates target skill gaps and progress, and ranks up to three eligible development activities. Ranking and progress are deterministic Python calculations. The original files in `backend/data/` are never mutated.

## Run

Python 3.11+ is recommended.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

OpenAPI docs are available at `http://127.0.0.1:8000/docs`.

The optional `.env.example` documents `OPENAI_API_KEY` and `OPENAI_MODEL`. Export them in the shell when using explanation enrichment. The API remains fully functional without either variable. OpenAI may rewrite only human-readable explanation text and evidence; it cannot change candidate IDs, scores, ordering, skill impacts, or progress. Any SDK, timeout, parsing, or validation failure falls back to deterministic explanations.

## API

- `GET /api/health` - load state, employee count, and OpenAI availability.
- `GET /api/employees?search=backend&limit=20` - lightweight employee selector data.
- `GET /api/employees/{employee_id}` - profile, resolved target, effective skills, gaps, progress, and recent history.
- `POST /api/employees/{employee_id}/recommendations` - deterministic ranked recommendations. Optional JSON body: `{"max_recommendations": 3}`.
- `POST /api/employees/{employee_id}/complete` - simulate completion with `{"event_id":"EV_006"}`.
- `GET /api/hr/summary` - aggregate gap, participation, and no-next-step metrics.
- `POST /api/import` - merge additional `employees` and `activity_history` arrays. A multipart request may provide an `employees` JSON file and an `activity_history` CSV file.
- `POST /api/reset` - restore the original in-memory snapshot.

## Demo flow

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/employees/E0002
curl -X POST http://127.0.0.1:8000/api/employees/E0002/recommendations \
  -H 'content-type: application/json' -d '{"max_recommendations":3}'
curl -X POST http://127.0.0.1:8000/api/employees/E0002/complete \
  -H 'content-type: application/json' -d '{"event_id":"EV_006"}'
curl -X POST http://127.0.0.1:8000/api/reset
```

The completion endpoint uses runtime memory only. It enforces current-role/current-grade eligibility, prerequisites, future sessions, and duplicate completion rules. The fixed dataset date is `2026-10-01`; machine time is not used for decisions.

## Design notes

- Mandatory events are excluded from personalized recommendations because the dataset README defines them as HR-assigned activities.
- Scheduled events require a session on or after the fixed snapshot date. Self-paced events with no sessions are available.
- A target comes from `career_goal`, otherwise the next grade in the same role. A Lead without an explicit goal has no fabricated promotion target.
- Progress is a weighted average of `min(current / required, 1)`, with critical skills weighted 1.5 and normal required skills weighted 1.0, clamped to 0-100.
- Ranking combines gap coverage, critical coverage, history fit, potential gain, and relevant breadth with weights 0.45/0.25/0.15/0.10/0.05. History penalties are bounded and ties use `event_id`.

## Tests

```bash
pytest -q
```

Tests cover loader validation, target resolution, post-review gains, eligibility, adversarial ranking, deterministic ties, completion/reset, imports, API routes, and OpenAI fallback behavior.
