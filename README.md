# Career Quest frontend

Career Quest is a desktop-first React/Vite frontend for employee career development. It supports the end-to-end demo flow in mock mode and keeps the real API behind the same typed client abstraction.

## Run

```bash
npm install
npm run dev
```

Copy `.env.example` to `.env` to configure `VITE_API_URL` and `VITE_USE_MOCKS`. Set `VITE_USE_MOCKS=false` to use the backend contract.

## Backend integration

With the backend running locally, use:

```env
VITE_API_URL=http://localhost:8000
VITE_USE_MOCKS=false
```

The API client normalizes the backend responses into the frontend model. It supports the current backend shapes for employee profiles (`career_progress`, `skill_gaps`, `recent_activity_history`), recommendations (`skill_name`, `after_if_completed`, optional activity metadata), HR summary aggregates, and import counts.

The main demo flow is: choose an employee → inspect the target and skill gaps → request up to three recommendations → open the evidence → complete an activity → reload the profile and recommendations → review the HR overview.
