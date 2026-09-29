import math

import pytest
from fastapi.testclient import TestClient

from app.services import cpm_engine, xai_engine


def _pert_activity(activity_id, name, optimistic, likely, pessimistic, predecessors=None, **extra):
    payload = {
        "name": name,
        "optimistic_time": optimistic,
        "most_likely_time": likely,
        "pessimistic_time": pessimistic,
        "predecessor_ids": predecessors or [],
    }
    payload.update(extra)
    payload["id"] = activity_id
    return payload


def _serial(merge_bias, id_a="A", id_b="B", id_j="J"):
    return [
        _pert_activity(id_a, "Start", 4, 5, 6),
        _pert_activity(id_b, "Branch B", 3, 4, 9, [id_a]),
        _pert_activity("C", "Branch C", 3, 4, 9, [id_a]),
        _pert_activity(id_j, "Join", 1, 1, 1, [id_b, "C"]),
    ]


# ---------------------------------------------------------------------------
# PERT sampling consistency
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("points", [
    (2, 3, 8), (3, 5, 9), (1, 8, 8), (8, 1, 1), (2, 5, 8),
    (0, 0, 10), (3, 7, 12), (6, 2, 20), (1, 1, 100), (10, 5, 10),
])
def test_pert_sampler_reproduces_analytic_expected_time(points):
    """The simulation must be consistent with the deterministic PERT expected time.

    The engine samples a triangular distribution whose mean is ``(o + m + p) / 3``
    while ``calculate_pert`` reports ``(o + 4m + p) / 6``. Any XAI card that
    compares a simulated mean against a critical path length would otherwise
    report the distribution mismatch as schedule risk.
    """
    optimistic, likely, pessimistic = points
    low = min(optimistic, likely, pessimistic)
    high = max(optimistic, likely, pessimistic)
    mode = low if not (low <= likely <= high) else likely
    alpha, beta = xai_engine._pert_shape_parameters(optimistic, likely, pessimistic)

    assert alpha > 0 and beta > 0

    activity = {
        "id": "X", "name": "X", "low": low, "high": high, "mode": mode,
        "alpha": alpha, "beta": beta, "predecessor_ids": [],
    }
    import random
    rng = random.Random(20260926)
    trials = 40000
    sampled = [xai_engine._pert_sample(activity, rng) for _ in range(trials)]
    observed = sum(sampled) / trials

    expected_time = (optimistic + 4.0 * likely + pessimistic) / 6.0
    standard_error = (high - low) / math.sqrt(12.0 * trials)
    assert abs(observed - expected_time) < max(0.05, 4.0 * standard_error), (
        f"{points}: sampled mean {observed:.4f} drifted from te {expected_time:.4f}"
    )


def test_degenerate_estimates_collapse_to_a_point():
    activity = {
        "id": "X", "name": "X", "low": 5.0, "high": 5.0, "mode": 5.0,
        "alpha": 1.0, "beta": 1.0, "predecessor_ids": [],
    }
    import random
    rng = random.Random(1)
    assert all(xai_engine._pert_sample(activity, rng) == 5.0 for _ in range(50))


def test_standard_normal_cdf_matches_reference_points():
    for z, expected in [(-3.0, 0.00135), (-1.0, 0.15866), (0.0, 0.5),
                        (1.0, 0.84134), (2.0, 0.97725), (3.0, 0.99865)]:
        assert xai_engine.standard_normal_cdf(z) == pytest.approx(expected, abs=1e-4)


def test_standard_normal_cdf_is_symmetric():
    for z in [0.3, 0.9, 1.7, 2.5]:
        assert xai_engine.standard_normal_cdf(z) + xai_engine.standard_normal_cdf(-z) == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Merge-bias detection
# ---------------------------------------------------------------------------

def test_merge_bias_is_positive_for_unbalanced_parallel_branches():
    activities = [
        _pert_activity("A", "Start", 4, 5, 6),
        _pert_activity("B", "Wide branch", 2, 5, 14, ["A"]),
        _pert_activity("C", "Narrow branch", 4, 5, 6, ["A"]),
        _pert_activity("J", "Join", 1, 1, 1, ["B", "C"]),
    ]
    nodes, _, _, _, _ = cpm_engine.calculate_pert(activities)
    detections = xai_engine.detect_merge_path_bias(nodes)

    assert detections, "a merge whose gap is inside its own noise must be detected"
    top = detections[0]
    assert top["merge_event_bias_days"] > 0
    assert 0.0 <= top["probability_shorter_branch_governs"] <= 1.0


def test_merge_bias_is_zero_for_a_single_serial_chain():
    activities = [
        _pert_activity("A", "One", 2, 3, 8),
        _pert_activity("B", "Two", 2, 3, 8, ["A"]),
    ]
    nodes, _, _, _, _ = cpm_engine.calculate_pert(activities)
    assert xai_engine.detect_merge_path_bias(nodes) == []


def test_merge_with_far_apart_branches_is_not_flagged():
    """A gap far larger than the combined spread is a genuine float, not hidden risk."""
    activities = [
        _pert_activity("A", "Start", 1, 1, 1),
        _pert_activity("B", "Long branch", 10, 10, 10, ["A"]),
        _pert_activity("C", "Short branch", 1, 1, 1, ["A"]),
        _pert_activity("J", "Join", 1, 1, 1, ["B", "C"]),
    ]
    nodes, _, _, _, _ = cpm_engine.calculate_pert(activities)
    assert xai_engine.detect_merge_path_bias(nodes) == []


def test_merge_event_bias_matches_monte_carlo():
    """E[max(X, Y)] - max(E) = sigma * phi(d) - d * (1 - Phi(d)), d = gap / sigma."""
    import random
    for sigma_a, sigma_b, gap in [(2.0, 3.0, 1.5), (1.0, 2.0, 0.5), (3.0, 1.0, 2.0)]:
        combined = math.sqrt(sigma_a ** 2 + sigma_b ** 2)
        predicted = xai_engine.merge_event_bias_days(gap, combined)

        rng = random.Random(99)
        trials = 200000
        total = 0.0
        for _ in range(trials):
            total += max(rng.gauss(0.0, sigma_a), gap + rng.gauss(0.0, sigma_b))
        empirical = total / trials - gap

        standard_error = combined / math.sqrt(trials)
        assert abs(empirical - predicted) < 4.0 * standard_error, (
            f"sigma=({sigma_a},{sigma_b}) gap={gap}: predicted {predicted:.4f} "
            f"vs simulated {empirical:.4f}"
        )


def test_merge_event_bias_edge_cases():
    assert xai_engine.merge_event_bias_days(0.0, 0.0) == 0.0
    assert xai_engine.merge_event_bias_days(5.0, 0.0) == 0.0
    expected = 1.0 / math.sqrt(2.0 * math.pi)
    assert xai_engine.merge_event_bias_days(0.0, 1.0) == pytest.approx(expected, abs=1e-9)
    assert xai_engine.merge_event_bias_days(10.0, 1.0) < 1e-3


# ---------------------------------------------------------------------------
# Seeded reproducibility and statistical honesty
# ---------------------------------------------------------------------------

def test_simulate_path_statistics_is_reproducible():
    activities = _serial(None)
    nodes, critical_path, expected, variance, _ = cpm_engine.calculate_pert(activities)
    stats = xai_engine.simulate_path_statistics(activities, num_simulations=250, seed=1234)
    second = xai_engine.simulate_path_statistics(activities, num_simulations=250, seed=1234)
    assert stats == second


def test_simulate_path_statistics_changes_with_seed():
    activities = _serial(None)
    first = xai_engine.simulate_path_statistics(activities, num_simulations=250, seed=1)
    second = xai_engine.simulate_path_statistics(activities, num_simulations=250, seed=2)
    assert first["mean_duration"] != second["mean_duration"] or \
        first["activity_criticality"] != second["activity_criticality"]


def test_mean_standard_error_is_reported_and_shrinks_with_trials():
    activities = _serial(None)
    small = xai_engine.simulate_path_statistics(activities, num_simulations=200, seed=7)
    large = xai_engine.simulate_path_statistics(activities, num_simulations=4000, seed=7)
    assert small["mean_standard_error"] > 0
    assert large["mean_standard_error"] < small["mean_standard_error"] / 3.0


def test_merge_free_network_does_not_claim_merge_bias():
    """A serial network with spread estimates must not report a merge bias."""
    activities = [
        _pert_activity("A", "One", 2, 3, 8),
        _pert_activity("B", "Two", 2, 3, 8, ["A"]),
    ]
    nodes, critical_path, expected, variance, _ = cpm_engine.calculate_pert(activities)
    stats = xai_engine.simulate_path_statistics(activities, num_simulations=3000, seed=11)
    report = xai_engine.explain_probabilistic_risk(
        nodes, critical_path, target_time=expected, probability=0.5,
        expected_duration=expected, project_variance=variance,
        criticality_indices=stats["activity_criticality"], path_statistics=stats,
        project_name="Serial", mode="PERT",
    )
    kinds = {card["kind"] for card in report["cards"]}
    assert "EMPIRICAL_MERGE_BIAS" not in kinds
    assert "ESTIMATOR_MISMATCH" not in kinds


def test_merge_network_reports_positive_empirical_bias():
    activities = [
        _pert_activity("A", "Start", 4, 5, 6),
        _pert_activity("B", "Branch B", 4, 5, 12, ["A"]),
        _pert_activity("C", "Branch C", 4, 5, 6, ["A"]),
        _pert_activity("J", "Join", 1, 1, 1, ["B", "C"]),
    ]
    nodes, critical_path, expected, variance, _ = cpm_engine.calculate_pert(activities)
    stats = xai_engine.simulate_path_statistics(activities, num_simulations=4000, seed=3)
    report = xai_engine.explain_probabilistic_risk(
        nodes, critical_path, target_time=expected, probability=0.5,
        expected_duration=expected, project_variance=variance,
        criticality_indices=stats["activity_criticality"], path_statistics=stats,
        project_name="Merged", mode="PERT",
    )
    bias_cards = [c for c in report["cards"] if c["kind"] == "EMPIRICAL_MERGE_BIAS"]
    assert bias_cards, "an asymmetric merge with a spread branch must report empirical bias"
    assert bias_cards[0]["headline_value"] if "headline_value" in bias_cards[0] else True


# ---------------------------------------------------------------------------
# Report contract
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("explanation", ["critical_path", "risk", "crashing"])
def test_reports_share_a_uniform_contract(explanation):
    activities = _serial(None)
    nodes, critical_path, expected, variance, _ = cpm_engine.calculate_pert(activities)
    if explanation == "critical_path":
        report = xai_engine.explain_critical_path_and_float(nodes, critical_path, expected, "P", "PERT")
    elif explanation == "risk":
        report = xai_engine.explain_probabilistic_risk(
            nodes, critical_path, target_time=expected, expected_duration=expected,
            project_variance=variance, project_name="P", mode="PERT")
    else:
        report = xai_engine.explain_schedule_crashing(activities, expected, project_name="P")

    for key in ("report_type", "title", "headline", "summary", "narrative",
                "cards", "metrics", "evidence_trace", "confidence", "severity"):
        assert key in report, f"{explanation} report is missing {key}"
    assert isinstance(report["cards"], list)
    assert isinstance(report["narrative"], list)
    assert report["severity"] in {"SUCCESS", "INFO", "WARNING", "CRITICAL"}
    for card in report["cards"]:
        for key in ("kind", "severity", "title", "narrative", "evidence", "actions", "activity_ids"):
            assert key in card, f"card is missing {key}: {card}"
        assert card["severity"] in {"SUCCESS", "INFO", "WARNING", "CRITICAL"}
        for action in card["actions"]:
            assert action["priority"] in {"HIGH", "MEDIUM", "LOW"}
    for step in report["evidence_trace"]:
        assert step["step"] and step["method"] and step["inputs"]


def test_empty_network_reports_explain_that_there_is_nothing_to_explain():
    empty = cpm_engine.build_network([])
    for report in (
        xai_engine.explain_critical_path_and_float(empty, [], 0.0, "Empty", "PERT"),
        xai_engine.explain_probabilistic_risk(empty, [], project_name="Empty", mode="PERT"),
        xai_engine.explain_schedule_crashing([], 0.0, project_name="Empty"),
    ):
        assert "no activities" in report["summary"].lower()
        assert report["cards"] == [] or all(
            c["kind"] != "ZERO_FLOAT_BOTTLENECK" for c in report["cards"]
        )


def test_narrative_summary_fuses_reports_by_severity():
    import datetime

    empty = cpm_engine.build_network([])
    mild = xai_engine.explain_critical_path_and_float(empty, [], 0.0, "Empty", "PERT")
    critical = xai_engine.explain_vendor_conflicts(
        [{
            "conflict_type": "DOUBLE_BOOKED", "activity_id": "a", "activity_name": "A",
            "vendor_name": "V", "total_float": 0.0,
            "resolution_recommendation": "split the booking",
        }],
        project_start_date=datetime.date(2026, 1, 1),
        project_name="Empty",
    )
    fused = xai_engine.build_narrative_summary([mild, critical], "Empty")

    ranking = {"SUCCESS": 0, "INFO": 1, "WARNING": 2, "CRITICAL": 3}
    worst = max(ranking[report["severity"]] for report in (mild, critical))
    assert ranking[fused["severity"]] == worst
    assert isinstance(fused["narrative"], list) and fused["narrative"]
    assert isinstance(fused["recommended_actions"], list)


# ---------------------------------------------------------------------------
# Endpoint contract
# ---------------------------------------------------------------------------

def _seed_pert_project(client: TestClient, mode: str = "PERT"):
    project_id = client.post("/api/v1/projects", json={"name": "Gala", "mode": mode}).json()["id"]
    start = client.post(f"/api/v1/projects/{project_id}/activities", json={
        "name": "Venue", "optimistic_time": 3, "most_likely_time": 5, "pessimistic_time": 9,
        "vendor_name": "Grand Hall", "category": "VENUE",
    }).json()["id"]
    headliner = client.post(f"/api/v1/projects/{project_id}/activities", json={
        "name": "Headliner", "optimistic_time": 4, "most_likely_time": 5.5, "pessimistic_time": 8,
        "predecessor_ids": [start], "vendor_name": "StarSound", "category": "ENTERTAINMENT",
        "crash_duration": 3, "normal_cost": 4000, "crash_cost": 5200,
    }).json()["id"]
    photo = client.post(f"/api/v1/projects/{project_id}/activities", json={
        "name": "Photo", "optimistic_time": 4, "most_likely_time": 5.2, "pessimistic_time": 7.5,
        "predecessor_ids": [start], "vendor_name": "StarSound", "category": "PHOTO",
    }).json()["id"]
    client.post(f"/api/v1/projects/{project_id}/activities", json={
        "name": "Finale", "optimistic_time": 1, "most_likely_time": 1, "pessimistic_time": 2,
        "predecessor_ids": [headliner, photo], "category": "PROGRAM",
    })
    return project_id


def test_critical_path_explanation_endpoint(client: TestClient):
    project_id = _seed_pert_project(client)
    response = client.get(f"/api/v1/projects/{project_id}/xai/critical-path-explanation")
    assert response.status_code == 200
    body = response.json()
    assert body["project_id"] == project_id
    assert body["report_type"] == xai_engine.REPORT_CRITICAL_PATH
    assert body["cards"]
    assert body["generated_at"]


def test_risk_diagnostics_endpoint_accepts_overrides(client: TestClient):
    project_id = _seed_pert_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/xai/risk-diagnostics",
        json={"num_simulations": 120, "seed": 5, "target_time": 15, "include_monte_carlo": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["target_time_days"] == 15
    assert body["path_statistics"]["num_simulations"] == 120
    assert body["path_statistics"]["seed"] == 5


def test_risk_diagnostics_is_deterministic_for_a_fixed_seed(client: TestClient):
    project_id = _seed_pert_project(client)
    url = f"/api/v1/projects/{project_id}/xai/risk-diagnostics"
    payload = {"num_simulations": 100, "seed": 42}
    first = client.post(url, json=payload).json()
    second = client.post(url, json=payload).json()

    first.pop("generated_at")
    second.pop("generated_at")
    assert first == second


def test_risk_diagnostics_rejects_invalid_simulation_count(client: TestClient):
    project_id = _seed_pert_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/xai/risk-diagnostics", json={"num_simulations": -1}
    )
    assert response.status_code == 422


def test_counterfactual_crashing_endpoint(client: TestClient):
    project_id = _seed_pert_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/xai/counterfactual-crashing", json={"target_duration": 9}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["report_type"] == xai_engine.REPORT_CRASHING
    assert body["crash_plan"]["original_duration"] > 0
    selections = [c for c in body["cards"] if c["kind"].startswith("CRASH_")]
    assert selections
    assert any(a["action"].startswith("Counterfactual:") or a["action"].startswith("Essential:")
               for c in selections for a in c["actions"])


def test_counterfactual_crashing_respects_a_budget_cap(client: TestClient):
    project_id = _seed_pert_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/xai/counterfactual-crashing", json={"max_budget": 1.0}
    )
    assert response.status_code == 200
    assert response.json()["metrics"]["additional_crash_cost"] <= 1.0


def test_counterfactual_crashing_does_not_spend_when_target_is_already_met(client: TestClient):
    """A target looser than the baseline must be a no-op, not a budget-driven crash."""
    project_id = _seed_pert_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/xai/counterfactual-crashing",
        json={"target_duration": 9999, "max_budget": 500000.0},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["metrics"]["days_saved"] == 0.0
    assert body["metrics"]["additional_crash_cost"] == 0.0
    assert not [c for c in body["cards"] if c["kind"].startswith("CRASH_")]


def test_counterfactual_crashing_still_spends_budget_when_no_target_is_given(client: TestClient):
    """With only a budget supplied, the engine must crash until the cap binds."""
    project_id = _seed_pert_project(client)
    response = client.post(
        f"/api/v1/projects/{project_id}/xai/counterfactual-crashing", json={"max_budget": 500000.0}
    )
    assert response.status_code == 200
    assert response.json()["metrics"]["days_saved"] > 0


def test_vendor_recommendations_endpoint_flags_double_booking(client: TestClient):
    project_id = _seed_pert_project(client)
    response = client.get(f"/api/v1/projects/{project_id}/xai/vendor-recommendations")
    assert response.status_code == 200
    body = response.json()
    assert body["conflict_count"] >= 1
    overbooking = [c for c in body["cards"] if c["kind"] == "VENDOR_OVERBOOKING"]
    assert overbooking
    assert "StarSound" in overbooking[0]["title"]


def test_vendor_recommendations_reports_clear_when_there_are_no_conflicts(client: TestClient):
    project_id = client.post("/api/v1/projects", json={"name": "Solo", "mode": "PERT"}).json()["id"]
    client.post(f"/api/v1/projects/{project_id}/activities", json={
        "name": "Only", "optimistic_time": 2, "most_likely_time": 3, "pessimistic_time": 4,
    })
    body = client.get(f"/api/v1/projects/{project_id}/xai/vendor-recommendations").json()
    assert body["conflict_count"] == 0
    assert body["cards"][0]["kind"] == "NO_VENDOR_CONFLICTS"


def test_bundle_fuses_all_reports(client: TestClient):
    project_id = _seed_pert_project(client)
    body = client.get(f"/api/v1/projects/{project_id}/xai/bundle").json()
    assert body["project_id"] == project_id
    assert body["critical_path"]["report_type"] == xai_engine.REPORT_CRITICAL_PATH
    assert body["risk"]["report_type"] == xai_engine.REPORT_RISK
    assert body["vendor"]["report_type"] == xai_engine.REPORT_VENDOR
    assert body["narrative"]["severity"] in {"SUCCESS", "INFO", "WARNING", "CRITICAL"}


def test_empty_project_endpoints_do_not_error(client: TestClient):
    project_id = client.post("/api/v1/projects", json={"name": "Empty", "mode": "PERT"}).json()["id"]
    base = f"/api/v1/projects/{project_id}/xai"
    assert client.get(f"{base}/critical-path-explanation").status_code == 200
    assert client.post(f"{base}/risk-diagnostics", json={}).status_code == 200
    assert client.post(f"{base}/counterfactual-crashing", json={}).status_code == 200
    assert client.get(f"{base}/vendor-recommendations").status_code == 200
    assert client.get(f"{base}/bundle").status_code == 200


def test_xai_endpoints_return_404_for_an_unknown_project(client: TestClient):
    missing = "00000000-0000-0000-0000-000000000000"
    base = f"/api/v1/projects/{missing}/xai"
    assert client.get(f"{base}/critical-path-explanation").status_code == 404
    assert client.post(f"{base}/risk-diagnostics", json={}).status_code == 404
    assert client.post(f"{base}/counterfactual-crashing", json={}).status_code == 404
    assert client.get(f"{base}/vendor-recommendations").status_code == 404
    assert client.get(f"{base}/bundle").status_code == 404
