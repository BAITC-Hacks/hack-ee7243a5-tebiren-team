from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from app.config import AS_OF_DATE
from app.data_loader import load_dataset
from app.recommendation.engine import event_is_eligible_for_completion, recommendations, resolve_target
from app.services.progress import career_progress, effective_skills
from app.services.runtime_state import RuntimeState


def test_dataset_loads_and_has_fixed_snapshot(data_dir):
    dataset = load_dataset(data_dir)
    assert dataset.meta["as_of_date"] == AS_OF_DATE.isoformat()
    assert len(dataset.employees) == 200
    assert len(dataset.events) == 40
    assert len(dataset.skills) == 60
    assert len(dataset.history) == 2743


def test_target_rules_and_cross_role(data_dir):
    dataset = load_dataset(data_dir)
    profiles = {(item["role"], item["grade"]): item for item in dataset.role_profiles}
    assert resolve_target({"role": "Backend Engineer", "grade": "Junior", "career_goal": None}, profiles) == {
        "role": "Backend Engineer", "grade": "Middle"
    }
    assert resolve_target({"role": "Backend Engineer", "grade": "Lead", "career_goal": None}, profiles) is None
    assert resolve_target(
        {"role": "Data Analyst", "grade": "Middle", "career_goal": {"target_role": "Product Manager", "target_grade": "Middle"}},
        profiles,
    ) == {"role": "Product Manager", "grade": "Middle"}


def test_effective_skills_apply_completed_post_review_once_and_respect_caps():
    employee = {"employee_id": "E1", "skills": {"SK": 1}, "last_review_date": "2026-01-01"}
    event = {"event_id": "EV", "develops_skills": [{"skill_id": "SK", "gain": 3, "max_level": 3}]}
    history = [
        {"record_id": "R1", "employee_id": "E1", "event_id": "EV", "date": "2026-02-01", "status": "completed"},
        {"record_id": "R2", "employee_id": "E1", "event_id": "EV", "date": "2026-03-01", "status": "completed"},
        {"record_id": "R3", "employee_id": "E1", "event_id": "EV", "date": "2026-04-01", "status": "no_show"},
    ]
    assert effective_skills(employee, history, {"EV": event}) == {"SK": 3}


def test_career_progress_weights_critical_and_clamps():
    profile = {"required_skills": {"critical": 4, "normal": 4}, "critical_skills": ["critical"]}
    assert career_progress(profile, {"critical": 2, "normal": 4}) == 70.0
    assert career_progress(profile, {"critical": 5, "normal": 5}) == 100.0


class MiniState:
    def __init__(self):
        self.employees = {
            "E1": {
                "employee_id": "E1", "full_name": "Adversarial Fixture", "department": "Test",
                "role": "Test Role", "grade": "Middle", "career_goal": {"target_role": "Test Role", "target_grade": "Senior"},
                "skills": {"SK_WEAK": 0, "SK_CRITICAL": 2}, "last_review_date": "2026-01-01",
            }
        }
        self._events = [
            {"event_id": "EV_WEAK", "title": "Weak skill class", "type": "course", "format": "self_paced", "mandatory": False,
             "target_roles": ["Test Role"], "target_grades": ["Middle"], "develops_skills": [{"skill_id": "SK_WEAK", "gain": 1, "max_level": 5}], "prerequisites": {}, "upcoming_sessions": []},
            {"event_id": "EV_CRITICAL", "title": "Critical skill workshop", "type": "workshop", "format": "self_paced", "mandatory": False,
             "target_roles": ["Test Role"], "target_grades": ["Middle"], "develops_skills": [{"skill_id": "SK_CRITICAL", "gain": 1, "max_level": 5}], "prerequisites": {}, "upcoming_sessions": []},
        ]
        self.dataset = SimpleNamespace(events=self._events)
        self._profiles = [{"role": "Test Role", "grade": "Senior", "required_skills": {"SK_WEAK": 5, "SK_CRITICAL": 3}, "critical_skills": ["SK_CRITICAL"]}]
        self._skills = [{"skill_id": "SK_WEAK", "name": "Weak Skill"}, {"skill_id": "SK_CRITICAL", "name": "Critical Skill"}]
        self.history = [{"record_id": "R1", "employee_id": "E1", "event_id": "EV_WEAK", "date": "2026-02-01", "status": "no_show"}]

    @property
    def role_profiles_by_key(self):
        return {(p["role"], p["grade"]): p for p in self._profiles}

    @property
    def skills_by_id(self):
        return {s["skill_id"]: s for s in self._skills}

    @property
    def events_by_id(self):
        return {e["event_id"]: e for e in self._events}

    def employee(self, employee_id):
        return self.employees.get(employee_id)

    def employee_history(self, employee_id):
        return [row for row in self.history if row["employee_id"] == employee_id]


def test_critical_gap_beats_weaker_irrelevant_history_fixture():
    result = recommendations(MiniState(), "E1", enrich_explanations=False)
    assert [item["event_id"] for item in result["recommendations"]] == ["EV_CRITICAL", "EV_WEAK"]


def test_prerequisite_and_current_grade_are_hard_constraints(data_dir):
    state = RuntimeState(load_dataset(data_dir))
    eligible, reason = event_is_eligible_for_completion(state, "E0002", "EV_006")
    assert eligible is False
    assert "prerequisite" in reason
    junior = next(employee for employee in state.employees.values() if employee["grade"] == "Junior" and employee["role"] == "Backend Engineer")
    eligible, reason = event_is_eligible_for_completion(state, junior["employee_id"], "EV_006")
    assert eligible is False
    assert "current grade" in reason


def test_recommendation_order_is_deterministic(data_dir):
    state = RuntimeState(load_dataset(data_dir))
    first = recommendations(state, "E0002", enrich_explanations=False)
    second = recommendations(state, "E0002", enrich_explanations=False)
    assert [(x["event_id"], x["score"]) for x in first["recommendations"]] == [(x["event_id"], x["score"]) for x in second["recommendations"]]


def test_openai_error_cannot_break_recommendations(data_dir, monkeypatch):
    state = RuntimeState(load_dataset(data_dir))
    from app.recommendation import engine

    monkeypatch.setattr(engine.OpenAIExplainer, "explain", lambda self, candidates: (_ for _ in ()).throw(TimeoutError()))
    result = recommendations(state, "E0002")
    assert result["recommendations"]
    assert all(item["explanation_source"] == "deterministic" for item in result["recommendations"])


def test_valid_openai_explanation_cannot_change_ranked_candidates(data_dir, monkeypatch):
    state = RuntimeState(load_dataset(data_dir))
    from app.recommendation import engine

    monkeypatch.setattr(
        engine.OpenAIExplainer,
        "explain",
        lambda self, candidates: {item["event_id"]: {"explanation": "validated", "reasons": ["evidence"]} for item in candidates},
    )
    result = recommendations(state, "E0002")
    assert result["recommendations"][0]["explanation_source"] == "openai"
    assert result["recommendations"][0]["score"] == 0.1991
    assert result["recommendations"][0]["event_id"] == "EV_005"


def test_empty_target_is_valid(data_dir):
    state = RuntimeState(load_dataset(data_dir))
    lead = next(e for e in state.employees.values() if e["grade"] == "Lead" and e["career_goal"] is None)
    result = recommendations(state, lead["employee_id"], enrich_explanations=False)
    assert result["target"] is None
    assert result["recommendations"] == []


def test_equal_scores_use_event_id_as_tie_breaker():
    state = MiniState()
    event_a = deepcopy(state._events[1])
    event_a["event_id"] = "EV_A"
    event_b = deepcopy(event_a)
    event_b["event_id"] = "EV_B"
    state._events = [event_b, event_a]
    state.dataset.events = state._events
    result = recommendations(state, "E1", enrich_explanations=False)
    ids = [item["event_id"] for item in result["recommendations"]]
    assert ids[:2] == ["EV_A", "EV_B"]
