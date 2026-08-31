from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

def test_create_and_query_cpm_project(client: TestClient):
    # 1. Create a project in CPM mode
    response = client.post(
        "/api/v1/projects",
        json={"name": "Test CPM Project", "description": "CPM Testing", "mode": "CPM"}
    )
    assert response.status_code == 201
    project = response.json()
    project_id = project["id"]
    assert project["name"] == "Test CPM Project"
    assert project["mode"] == "CPM"

    # 2. Add Activity A
    response = client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={"name": "Activity A", "duration": 5.0, "predecessor_ids": []}
    )
    assert response.status_code == 201
    act_a = response.json()
    act_a_id = act_a["id"]

    # 3. Add Activity B depending on A
    response = client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={"name": "Activity B", "duration": 7.0, "predecessor_ids": [act_a_id]}
    )
    assert response.status_code == 201
    act_b = response.json()
    act_b_id = act_b["id"]

    # 4. Fetch Project details with activities
    response = client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data["activities"]) == 2

    # 5. Query Network
    response = client.get(f"/api/v1/projects/{project_id}/network")
    assert response.status_code == 200
    net = response.json()
    assert len(net["nodes"]) == 4  # START, END, A, B
    assert net["critical_path"] == [act_a_id, act_b_id]
    
    # Check start and end node presence
    node_ids = [node["id"] for node in net["nodes"]]
    assert "START" in node_ids
    assert "END" in node_ids


def test_circular_dependency_rejection(client: TestClient):
    # 1. Create project
    response = client.post(
        "/api/v1/projects",
        json={"name": "Test Cycle Project", "mode": "CPM"}
    )
    project_id = response.json()["id"]

    # 2. Add Activity A
    response = client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={"name": "A", "duration": 3.0}
    )
    act_a_id = response.json()["id"]

    # 3. Add Activity B depending on A
    response = client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={"name": "B", "duration": 4.0, "predecessor_ids": [act_a_id]}
    )
    act_b_id = response.json()["id"]

    # 4. Try to update A to depend on B (creates a cycle: A -> B -> A)
    # This should be caught by our cycle detection and return a clean 400 Bad Request
    response = client.put(
        f"/api/v1/projects/{project_id}/activities/{act_a_id}",
        json={"predecessor_ids": [act_b_id]}
    )
    assert response.status_code == 400
    err_detail = response.json()
    assert "Circular dependency detected" in err_detail["detail"]
    assert act_a_id in err_detail["cycle_ids"] or act_b_id in err_detail["cycle_ids"]


def test_invalid_pert_estimate_ordering(client: TestClient):
    # 1. Create project in PERT mode
    response = client.post(
        "/api/v1/projects",
        json={"name": "Test PERT Project", "mode": "PERT"}
    )
    project_id = response.json()["id"]

    # 2. Try to add activity with invalid estimates (optimistic > most_likely)
    # Pydantic schema validation should catch this and return a 422 Unprocessable Entity
    response = client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={
            "name": "Activity Invalid",
            "optimistic_time": 10.0,
            "most_likely_time": 5.0,  # Invalid: lk < opt
            "pessimistic_time": 15.0
        }
    )
    assert response.status_code == 422
    assert "Value error" in response.text or "PERT estimates" in response.text

    # 3. Try to add activity with negative estimates
    response = client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={
            "name": "Activity Negative",
            "optimistic_time": -2.0,
            "most_likely_time": 3.0,
            "pessimistic_time": 5.0
        }
    )
    assert response.status_code == 422


def test_simulate_change_flips(client: TestClient):
    # 1. Create project
    response = client.post(
        "/api/v1/projects",
        json={"name": "Simulation Project", "mode": "CPM"}
    )
    project_id = response.json()["id"]

    # 2. Add Activity A (dur=10)
    response = client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={"name": "A", "duration": 10.0}
    )
    act_a_id = response.json()["id"]

    # 3. Add Activity B (dur=2, pred A) -> Path A-B = 12
    response = client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={"name": "B", "duration": 2.0, "predecessor_ids": [act_a_id]}
    )
    act_b_id = response.json()["id"]

    # 4. Add Activity C (dur=5) -> Path C = 5
    response = client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={"name": "C", "duration": 5.0}
    )
    act_c_id = response.json()["id"]

    # Baseline critical path: A -> B (length 12)
    # Activity C is non-critical.

    # 5. Simulate change: Modify C's duration to 15.0
    # Now Path C = 15, which is longer than Path A-B (12)
    # So C should become critical, and A and B should become non-critical
    response = client.post(
        f"/api/v1/projects/{project_id}/simulate",
        json={
            "activity_id": act_c_id,
            "duration": 15.0
        }
    )
    assert response.status_code == 200
    sim = response.json()
    
    assert sim["new_project_duration"] == 15.0
    assert act_c_id in sim["new_critical_path"]
    assert act_a_id not in sim["new_critical_path"]
    assert act_b_id not in sim["new_critical_path"]
    
    # Check flips
    assert act_c_id in sim["flipped_to_critical"]
    assert act_a_id in sim["flipped_to_non_critical"]
    assert act_b_id in sim["flipped_to_non_critical"]


def test_missing_resource_not_found(client: TestClient):
    # Test GET on non-existent project
    random_uuid = str(uuid4())
    response = client.get(f"/api/v1/projects/{random_uuid}")
    assert response.status_code == 404
    
    # Test POST activity to non-existent project
    response = client.post(
        f"/api/v1/projects/{random_uuid}/activities",
        json={"name": "Orphan Activity", "duration": 5.0}
    )
    assert response.status_code == 404


def test_rbac_authorization_enforcement(client: TestClient):
    # 1. Admin creates a project (X-User-Role: ADMIN) -> 201 Created
    response = client.post(
        "/api/v1/projects",
        json={"name": "RBAC Test Project", "mode": "CPM"},
        headers={"X-User-Role": "ADMIN"}
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    # 2. Standard User attempts to create a project (X-User-Role: USER) -> 403 Forbidden
    response = client.post(
        "/api/v1/projects",
        json={"name": "Unauthorized Project", "mode": "CPM"},
        headers={"X-User-Role": "USER"}
    )
    assert response.status_code == 403
    assert "Access denied" in response.text or "Admin role required" in response.text

    # 3. Standard User can read project details -> 200 OK
    response = client.get(
        f"/api/v1/projects/{project_id}",
        headers={"X-User-Role": "USER"}
    )
    assert response.status_code == 200

    # 4. Standard User attempts to add activity -> 403 Forbidden
    response = client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={"name": "Forbidden Activity", "duration": 5.0},
        headers={"X-User-Role": "USER"}
    )
    assert response.status_code == 403

    # 5. Standard User attempts to delete project -> 403 Forbidden
    response = client.delete(
        f"/api/v1/projects/{project_id}",
        headers={"X-User-Role": "USER"}
    )
    assert response.status_code == 403

    # 6. Admin deletes project -> 204 No Content
    response = client.delete(
        f"/api/v1/projects/{project_id}",
        headers={"X-User-Role": "ADMIN"}
    )
    assert response.status_code == 204


def test_export_csv_and_pdf(client: TestClient):
    # 1. Create project with activities
    response = client.post(
        "/api/v1/projects",
        json={"name": "Export Test Project", "description": "Testing exports", "mode": "CPM"}
    )
    assert response.status_code == 201
    project_id = response.json()["id"]

    client.post(
        f"/api/v1/projects/{project_id}/activities",
        json={"name": "Activity 1", "duration": 4.0}
    )

    # 2. Test CSV Export
    csv_res = client.get(f"/api/v1/projects/{project_id}/export/csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "EVENTPATH PROJECT REPORT" in csv_res.text
    assert "Export Test Project" in csv_res.text
    assert "Activity 1" in csv_res.text

    # 3. Test PDF Export
    pdf_res = client.get(f"/api/v1/projects/{project_id}/export/pdf")
    assert pdf_res.status_code == 200
    assert "application/pdf" in pdf_res.headers["content-type"]
    assert pdf_res.content.startswith(b"%PDF")


def test_activity_dependency_types_and_websocket(client: TestClient):
    # 1. Create project
    proj_res = client.post("/api/v1/projects", json={"name": "Dep Types Test", "mode": "CPM"})
    assert proj_res.status_code == 201
    pid = proj_res.json()["id"]

    # 2. Add Activity A
    act_a = client.post(f"/api/v1/projects/{pid}/activities", json={"name": "Act A", "duration": 5.0}).json()
    
    # 3. Add Activity B with SS (Start-to-Start) dependency & 2d lag
    act_b = client.post(f"/api/v1/projects/{pid}/activities", json={
        "name": "Act B",
        "duration": 4.0,
        "dependencies": [
            {"predecessor_id": act_a["id"], "dependency_type": "SS", "lag": 2.0}
        ]
    }).json()

    assert len(act_b["dependencies"]) == 1
    assert act_b["dependencies"][0]["dependency_type"] == "SS"
    assert act_b["dependencies"][0]["lag"] == 2.0

    # 4. Check network calculations with SS dependency
    net_res = client.get(f"/api/v1/projects/{pid}/network")
    assert net_res.status_code == 200
    net_data = net_res.json()
    
    nodes_map = {n["id"]: n for n in net_data["nodes"]}
    # Act A starts at 0, finishes at 5
    # Act B starts at ES = A.es + lag = 0 + 2 = 2.0, finishes at 2 + 4 = 6.0
    assert nodes_map[act_b["id"]]["es"] == 2.0
    assert nodes_map[act_b["id"]]["ef"] == 6.0

    # 5. Test WebSocket Connection & Ping/Pong
    with client.websocket_connect(f"/api/v1/projects/{pid}/ws") as websocket:
        websocket.send_text("ping")
        data = websocket.receive_json()
        assert data["type"] == "pong"
        assert data["project_id"] == pid


