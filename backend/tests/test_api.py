from __future__ import annotations

from fastapi.testclient import TestClient

from app import main


client = TestClient(main.app)


def setup_function():
    main.state.reset()


def test_core_api_flow_and_reset():
    assert client.get("/api/health").status_code == 200
    employees = client.get("/api/employees").json()
    assert len(employees["employees"]) == 200
    assert client.get("/api/employees/E0002").status_code == 200
    rec = client.post("/api/employees/E0002/recommendations", json={"max_recommendations": 3})
    assert rec.status_code == 200
    body = rec.json()
    assert 0 <= len(body["recommendations"]) <= 3
    assert body["recommendations"]
    chosen = body["recommendations"][0]["event_id"]
    history_before = len(main.state.history)
    completion = client.post("/api/employees/E0002/complete", json={"event_id": chosen})
    assert completion.status_code == 200
    assert len(main.state.history) == history_before + 1
    assert completion.json()["progress_after"] >= completion.json()["progress_before"]
    assert client.get("/api/hr/summary").status_code == 200
    assert client.post("/api/reset").json() == {"success": True}
    assert len(main.state.history) == 2743


def test_unknown_employee_and_import():
    assert client.get("/api/employees/NOPE").status_code == 404
    source = main.state.employees["E0001"].copy()
    source["employee_id"] = "E9001"
    response = client.post("/api/import", json={"employees": [source], "activity_history": []})
    assert response.status_code == 200
    assert response.json()["employees_added"] == 1
    assert client.get("/api/employees/E9001").status_code == 200
    assert client.post("/api/employees/E9001/recommendations", json={"max_recommendations": 3}).status_code == 200
    assert client.post("/api/import", json={"employees": [source], "activity_history": []}).status_code == 422
    main.state.reset()


def test_invalid_import_is_422():
    response = client.post("/api/import", json={"employees": [{"employee_id": "broken"}], "activity_history": []})
    assert response.status_code == 422
