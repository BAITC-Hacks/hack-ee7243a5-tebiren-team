from __future__ import annotations

import sys
import os
from pathlib import Path

import pytest

# Never initialize the developer's persistent database while collecting tests.
os.environ['CQ_DATABASE_PATH'] = ':memory:'
os.environ['OPENAI_API_KEY'] = ''
os.environ['OPENAI_API_KEY_FILE'] = ''
os.environ['CQ_HR_PASSWORD'] = ''
os.environ['CQ_EMPLOYEE_PASSWORD'] = ''


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture()
def data_dir() -> Path:
    return BACKEND_DIR / "data"
