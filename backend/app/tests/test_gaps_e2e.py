import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_db

# Setup test SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_gaps.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def test_gap1_free_float_and_network():
    """Gap 1: Verify total float, free float, and interfering float calculations in network endpoint."""
    proj_resp = client.post("/api/v1/projects", json={"name": "Float Test", "mode": "CPM"})
    assert proj_resp.status_code == 201
    pid = proj_resp.json()["id"]

    # Activity A: 5d (pred: None)
    a_resp = client.post(f"/api/v1/projects/{pid}/activities", json={"name": "Act A", "duration": 5})
    a_id = a_resp.json()["id"]

    # Activity B: 3d (pred: A) - Critical
    b_resp = client.post(f"/api/v1/projects/{pid}/activities", json={"name": "Act B", "duration": 3, "predecessor_ids": [a_id]})
    b_id = b_resp.json()["id"]

    # Activity C: 1d (pred: A) - Non-critical (2d float)
    c_resp = client.post(f"/api/v1/projects/{pid}/activities", json={"name": "Act C", "duration": 1, "predecessor_ids": [a_id]})
    c_id = c_resp.json()["id"]

    # Activity D: 2d (pred: B, C)
    d_resp = client.post(f"/api/v1/projects/{pid}/activities", json={"name": "Act D", "duration": 2, "predecessor_ids": [b_id, c_id]})
    d_id = d_resp.json()["id"]

    net_resp = client.get(f"/api/v1/projects/{pid}/network")
    assert net_resp.status_code == 200
    data = net_resp.json()

    nodes_by_id = {node["id"]: node for node in data["nodes"]}
    assert nodes_by_id[c_id]["total_float"] == 2.0
    assert nodes_by_id[c_id]["free_float"] == 2.0
    assert nodes_by_id[c_id]["is_critical"] is False
    assert nodes_by_id[a_id]["is_critical"] is True


def test_gap2_project_crashing_optimization():
    """Gap 2: Test schedule crashing endpoint for cost-optimal duration reduction."""
    proj_resp = client.post("/api/v1/projects", json={"name": "Crash Test", "mode": "CPM"})
    pid = proj_resp.json()["id"]

    a_resp = client.post(f"/api/v1/projects/{pid}/activities", json={
        "name": "Task A",
        "duration": 10,
        "crash_duration": 6,
        "normal_cost": 1000,
        "crash_cost": 1800  # cost per day = (1800-1000)/(10-6) = 200
    })
    a_id = a_resp.json()["id"]

    b_resp = client.post(f"/api/v1/projects/{pid}/activities", json={
        "name": "Task B",
        "duration": 5,
        "crash_duration": 3,
        "normal_cost": 500,
        "crash_cost": 1100, # cost per day = (1100-500)/(5-3) = 300
        "predecessor_ids": [a_id]
    })

    # Baseline duration: 15 days. Request crash to target_duration: 12 days
    crash_resp = client.post(f"/api/v1/projects/{pid}/crash", json={"target_duration": 12})
    assert crash_resp.status_code == 200
    res = crash_resp.json()

    assert res["original_duration"] == 15.0
    assert res["crashed_duration"] == 12.0
    assert res["total_days_saved"] == 3.0
    assert res["additional_crash_cost"] == 600.0  # 3 days * 200/day for Task A


def test_gap3_monte_carlo_simulation():
    """Gap 3: Test Monte Carlo PERT simulation & S-Curve risk analysis."""
    proj_resp = client.post("/api/v1/projects", json={"name": "Monte Carlo Test", "mode": "PERT"})
    pid = proj_resp.json()["id"]

    client.post(f"/api/v1/projects/{pid}/activities", json={
        "name": "PERTA",
        "optimistic_time": 2, "most_likely_time": 5, "pessimistic_time": 10
    })

    mc_resp = client.post(f"/api/v1/projects/{pid}/monte-carlo", json={"num_simulations": 500, "target_time": 6})
    assert mc_resp.status_code == 200
    res = mc_resp.json()

    assert res["num_simulations"] == 500
    assert "mean_duration" in res
    assert "p50" in res
    assert "s_curve" in res
    assert len(res["s_curve"]) > 0
    assert len(res["criticality_indices"]) > 0


def test_gap4_event_templates():
    """Gap 4: Test pre-built event template instantiation."""
    tpl_resp = client.post("/api/v1/projects/template/WEDDING_STANDARD")
    assert tpl_resp.status_code == 201
    data = tpl_resp.json()

    assert data["name"] == "Grand Wedding Ceremony & Reception"
    assert data["category"] == "WEDDING"
    assert len(data["activities"]) >= 8


def test_gap5_vendor_availability_checks():
    """Gap 5: Test vendor availability and overbooking verification engine."""
    proj_resp = client.post("/api/v1/projects", json={"name": "Vendor Test", "mode": "CPM"})
    pid = proj_resp.json()["id"]

    today = date.today()
    # Vendor available starting 10 days from today
    v_from = today + timedelta(days=10)
    v_to = today + timedelta(days=20)

    client.post(f"/api/v1/projects/{pid}/activities", json={
        "name": "Early Stage Setup",
        "duration": 5,
        "vendor_name": "StagePro Inc",
        "vendor_available_from": v_from.isoformat(),
        "vendor_available_to": v_to.isoformat()
    })

    chk_resp = client.get(f"/api/v1/projects/{pid}/availability")
    assert chk_resp.status_code == 200
    res = chk_resp.json()

    assert res["has_conflicts"] is True
    assert res["total_conflicts"] >= 1
    assert res["conflicts"][0]["conflict_type"] == "VENDOR_AVAILABILITY_VIOLATION"
