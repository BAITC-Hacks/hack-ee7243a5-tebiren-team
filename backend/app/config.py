from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date


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
    return os.getenv("OPENAI_API_KEY") or None, os.getenv("OPENAI_MODEL") or None


def openai_enabled() -> bool:
    key, model = openai_settings()
    return bool(key and model)
