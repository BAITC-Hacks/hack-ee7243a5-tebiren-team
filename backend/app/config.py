from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BACKEND_DIR / '.env', override=False)


def database_path() -> str:
    return os.getenv('CQ_DATABASE_PATH', str(BACKEND_DIR / 'var' / 'career-quest.sqlite3'))


def allowed_origins() -> list[str]:
    return [x.strip() for x in os.getenv('CQ_ALLOWED_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()]


AS_OF_DATE = date(2026, 10, 1)
GRADE_ORDER = ("Junior", "Middle", "Senior", "Lead")
REPEATABLE_EVENT_IDS = frozenset({"EV_036"})
MAX_PROFICIENCY = 5


@dataclass(frozen=True)
class ScoreWeights:
    gap_coverage: float = 0.45
    critical_coverage: float = 0.25
    history_fit: float = 0.15
    potential_gain: float = 0.10
    relevant_breadth: float = 0.05


SCORE_WEIGHTS = ScoreWeights()


def openai_settings() -> tuple[str | None, str | None]:
    key = os.getenv("OPENAI_API_KEY")
    # Explicitly configured local key file; its contents never reach the frontend.
    # An explicitly empty OPENAI_API_KEY disables AI, including during tests.
    key_file = os.getenv("OPENAI_API_KEY_FILE")
    if key is None and key_file:
        path = Path(key_file)
        if not path.is_absolute():
            path = BACKEND_DIR / path
        try:
            key = path.read_text(encoding="utf-8-sig").strip()
        except OSError:
            key = None
    return key or None, os.getenv("OPENAI_MODEL") or None


def openai_enabled() -> bool:
    key, model = openai_settings()
    return bool(key and model)
