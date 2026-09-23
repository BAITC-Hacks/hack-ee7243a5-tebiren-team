"""Opt-in local browser fault test; never used by npm run dev.

Run on separate ports with CQ_DATABASE_PATH pointing at ui-acceptance.sqlite3,
CQ_HR_PASSWORD / CQ_EMPLOYEE_PASSWORD set, and OPENAI_API_KEY explicitly empty.
Recommendations wait 3s; the first profile refresh after completion fails once.
"""
import asyncio
import os
from pathlib import Path

if Path(os.environ.get('CQ_DATABASE_PATH', '')).name != 'ui-acceptance.sqlite3':
    raise RuntimeError('UI harness requires its isolated ui-acceptance.sqlite3 database')
if os.environ.get('OPENAI_API_KEY') != '':
    raise RuntimeError('UI harness must disable paid OpenAI requests')

from fastapi.responses import JSONResponse
from app.main import app

pending_failures = set()


@app.middleware('http')
async def browser_fault_scenarios(request, call_next):
    path = request.url.path
    if path.endswith('/recommendations'):
        await asyncio.sleep(3)
    if request.method == 'GET' and path in pending_failures:
        pending_failures.remove(path)
        return JSONResponse({'detail': 'Simulated temporary profile refresh failure'}, status_code=503)
    response = await call_next(request)
    if path.endswith('/complete') and response.status_code == 200:
        pending_failures.add(path.removesuffix('/complete'))
    return response
