from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator


class Target(BaseModel):
    role: str
    grade: str


class SkillGap(BaseModel):
    skill_id: str
    skill_name: str
    current: int
    required: int
    gap: int
    critical: bool


class SkillImpact(BaseModel):
    skill_id: str
    skill_name: str
    before: int
    after_if_completed: int
    required: int
    critical: bool


class ActivityHistoryItem(BaseModel):
    record_id: str
    event_id: str
    title: str
    date: date
    status: str
    completion_pct: int
    due_date: date | None = None
    feedback_rating: int | None = None


class EmployeeSummary(BaseModel):
    employee_id: str
    full_name: str
    role: str
    grade: str


class EmployeeListResponse(BaseModel):
    employees: list[EmployeeSummary]


class EmployeeDetail(BaseModel):
    employee_id: str
    full_name: str
    department: str
    role: str
    grade: str
    tenure_months: int
    preferred_language: str
    career_goal: Target | None
    target: Target | None
    effective_skills: dict[str, int]
    required_target_skills: dict[str, int]
    skill_gaps: list[SkillGap]
    critical_skills: list[str]
    career_progress: float | None
    recent_activity_history: list[ActivityHistoryItem]


class ScoreBreakdown(BaseModel):
    gap_coverage: float
    critical_coverage: float
    history_fit: float
    potential_gain: float
    relevant_breadth: float


class Recommendation(BaseModel):
    rank: int
    event_id: str
    title: str
    score: float
    score_breakdown: ScoreBreakdown
    reasons: list[str]
    explanation: str | None = None
    skill_impacts: list[SkillImpact]
    explanation_source: str


class RecommendationsResponse(BaseModel):
    employee_id: str
    target: Target | None
    progress: float | None
    skill_gaps: list[SkillGap]
    recommendations: list[Recommendation]
    reason: str | None = None


class CompleteRequest(BaseModel):
    event_id: str = Field(min_length=1)


class UpdatedSkill(BaseModel):
    skill_id: str
    before: int
    after: int


class CompleteResponse(BaseModel):
    success: bool
    employee_id: str
    event_id: str
    progress_before: float | None
    progress_after: float | None
    updated_skills: list[UpdatedSkill]


class HealthResponse(BaseModel):
    status: str
    dataset_loaded: bool
    employees: int
    openai_enabled: bool


class ResetResponse(BaseModel):
    success: bool


class ImportResponse(BaseModel):
    success: bool
    employees_added: int
    history_rows_added: int
    warnings: list[str]


class RecommendationRequest(BaseModel):
    max_recommendations: int = Field(default=3, ge=1, le=3)


class ParticipationStats(BaseModel):
    total_records: int
    unique_participants: int
    status_counts: dict[str, int]
    completion_rate: float


class GapSummary(BaseModel):
    skill_id: str
    skill_name: str
    employees: int
    critical_for_target: int


class HRSummary(BaseModel):
    total_employees: int
    grade_distribution: dict[str, int]
    most_common_unresolved_target_gaps: list[GapSummary]
    participation: ParticipationStats
    employees_with_no_valid_next_step: int
    closest_to_target: list[dict[str, Any]]


class ImportPayload(BaseModel):
    employees: list[dict[str, Any]] = Field(default_factory=list)
    activity_history: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("activity_history", mode="before")
    @classmethod
    def accept_history_alias(cls, value: Any) -> Any:
        return value
