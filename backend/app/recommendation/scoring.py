from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..config import SCORE_WEIGHTS


def clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


@dataclass(frozen=True)
class CandidateScore:
    event: dict[str, Any]
    breakdown: dict[str, float]
    score: float
    penalty: float
    impacts: tuple[dict[str, Any], ...]


def _history_fit(event: dict[str, Any], history: list[dict[str, Any]], events_by_id: dict[str, dict[str, Any]]) -> tuple[float, float]:
    similar = [
        row
        for row in history
        if (past := events_by_id.get(row["event_id"]))
        and (past.get("type") == event.get("type") or past.get("format") == event.get("format"))
    ]
    value = 0.5
    penalty = 0.0
    for row in similar:
        if row["status"] == "completed":
            value += 0.05
        elif row["status"] == "no_show":
            value -= 0.08
            penalty += 0.03
        elif row["status"] == "dropped":
            value -= 0.06
            penalty += 0.02
        elif row["status"] == "declined":
            value -= 0.05
            penalty += 0.02
        elif row["status"] == "overdue":
            value -= 0.04
            penalty += 0.01
    return clamp(value), min(0.15, penalty)


def score_event(
    event: dict[str, Any],
    *,
    skills: dict[str, int],
    skill_gaps: list[dict[str, Any]],
    history: list[dict[str, Any]],
    events_by_id: dict[str, dict[str, Any]],
) -> CandidateScore:
    gaps_by_id = {gap["skill_id"]: gap for gap in skill_gaps if gap["gap"] > 0}
    impacts: list[dict[str, Any]] = []
    for item in event.get("develops_skills", []):
        gap = gaps_by_id.get(item["skill_id"])
        if not gap:
            continue
        before = skills.get(item["skill_id"], 0)
        after = min(before + int(item.get("gain", 0)), int(item.get("max_level", 5)), 5)
        effective_gain = max(0, min(after - before, gap["gap"]))
        if effective_gain <= 0:
            continue
        impacts.append({**gap, "before": before, "after_if_completed": after, "effective_gain": effective_gain})

    total_gap = sum(gap["gap"] for gap in gaps_by_id.values())
    critical_gaps = [gap for gap in gaps_by_id.values() if gap["critical"]]
    critical_total = sum(gap["gap"] for gap in critical_gaps)
    gained = sum(item["effective_gain"] for item in impacts)
    critical_gained = sum(item["effective_gain"] for item in impacts if item["critical"])
    gap_coverage = clamp(gained / total_gap) if total_gap else 0.0
    critical_coverage = clamp(critical_gained / critical_total) if critical_total else 0.0
    history_fit, penalty = _history_fit(event, history, events_by_id)
    potential_gain = clamp(gained / max(1, len(gaps_by_id)))
    relevant_breadth = clamp(len(impacts) / max(1, len(gaps_by_id)))
    breakdown = {
        "gap_coverage": gap_coverage,
        "critical_coverage": critical_coverage,
        "history_fit": history_fit,
        "potential_gain": potential_gain,
        "relevant_breadth": relevant_breadth,
    }
    raw = (
        breakdown["gap_coverage"] * SCORE_WEIGHTS.gap_coverage
        + breakdown["critical_coverage"] * SCORE_WEIGHTS.critical_coverage
        + breakdown["history_fit"] * SCORE_WEIGHTS.history_fit
        + breakdown["potential_gain"] * SCORE_WEIGHTS.potential_gain
        + breakdown["relevant_breadth"] * SCORE_WEIGHTS.relevant_breadth
    )
    return CandidateScore(event, breakdown, clamp(raw - penalty), penalty, tuple(impacts))
