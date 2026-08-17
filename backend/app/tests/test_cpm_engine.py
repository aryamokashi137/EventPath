import pytest
from app.services import cpm_engine

def test_linear_path():
    """
    Test Case 1: Simple linear network A -> B -> C
    Expected duration: 18
    Critical path: A, B, C
    """
    activities = [
        {"id": "A", "name": "Task A", "duration": 5.0, "predecessor_ids": []},
        {"id": "B", "name": "Task B", "duration": 10.0, "predecessor_ids": ["A"]},
        {"id": "C", "name": "Task C", "duration": 3.0, "predecessor_ids": ["B"]}
    ]
    
    nodes, critical_path, duration = cpm_engine.calculate_cpm(activities)
    
    assert duration == 18.0
    assert critical_path == ["A", "B", "C"]
    
    # Check start and end virtual nodes
    assert nodes["START"].es == 0.0
    assert nodes["START"].ef == 0.0
    assert nodes["END"].es == 18.0
    assert nodes["END"].ef == 18.0
    
    # Check intermediate nodes
    assert nodes["A"].es == 0.0
    assert nodes["A"].ef == 5.0
    assert nodes["B"].es == 5.0
    assert nodes["B"].ef == 15.0
    assert nodes["C"].es == 15.0
    assert nodes["C"].ef == 18.0

    # Slacks must be zero
    assert nodes["A"].slack == 0.0
    assert nodes["B"].slack == 0.0
    assert nodes["C"].slack == 0.0


def test_branching_merging():
    """
    Test Case 2: Branching and merging
    A -> B -> D
    A -> C -> D
    A: 2, B: 3, C: 4, D: 2
    Critical path: A -> C -> D (length 8)
    Non-critical path: A -> B -> D (length 7)
    """
    activities = [
        {"id": "A", "name": "Task A", "duration": 2.0, "predecessor_ids": []},
        {"id": "B", "name": "Task B", "duration": 3.0, "predecessor_ids": ["A"]},
        {"id": "C", "name": "Task C", "duration": 4.0, "predecessor_ids": ["A"]},
        {"id": "D", "name": "Task D", "duration": 2.0, "predecessor_ids": ["B", "C"]}
    ]

    nodes, critical_path, duration = cpm_engine.calculate_cpm(activities)

    assert duration == 8.0
    assert critical_path == ["A", "C", "D"]

    # Slack values
    assert nodes["A"].slack == 0.0
    assert nodes["C"].slack == 0.0
    assert nodes["D"].slack == 0.0
    assert nodes["B"].slack == 1.0  # LS=3, ES=2


def test_complex_network():
    """
    Test Case 3: Complex overlapping paths
    A: 3
    B: 4 (pred A)
    C: 2 (pred A)
    D: 5 (pred B)
    E: 1 (pred B, C)
    F: 3 (pred D, E)
    Expected critical path: A -> B -> D -> F (length 15)
    """
    activities = [
        {"id": "A", "name": "Task A", "duration": 3.0, "predecessor_ids": []},
        {"id": "B", "name": "Task B", "duration": 4.0, "predecessor_ids": ["A"]},
        {"id": "C", "name": "Task C", "duration": 2.0, "predecessor_ids": ["A"]},
        {"id": "D", "name": "Task D", "duration": 5.0, "predecessor_ids": ["B"]},
        {"id": "E", "name": "Task E", "duration": 1.0, "predecessor_ids": ["B", "C"]},
        {"id": "F", "name": "Task F", "duration": 3.0, "predecessor_ids": ["D", "E"]}
    ]

    nodes, critical_path, duration = cpm_engine.calculate_cpm(activities)

    assert duration == 15.0
    assert critical_path == ["A", "B", "D", "F"]

    # Verify slack values
    assert nodes["A"].slack == 0.0
    assert nodes["B"].slack == 0.0
    assert nodes["D"].slack == 0.0
    assert nodes["F"].slack == 0.0
    assert nodes["C"].slack == 6.0  # LS=9, ES=3
    assert nodes["E"].slack == 4.0  # LS=11, ES=7


def test_cycle_detection():
    """Verify that a cycle raises CycleDetectedError with the details."""
    activities = [
        {"id": "A", "name": "Task A", "duration": 2.0, "predecessor_ids": ["C"]},
        {"id": "B", "name": "Task B", "duration": 3.0, "predecessor_ids": ["A"]},
        {"id": "C", "name": "Task C", "duration": 4.0, "predecessor_ids": ["B"]}
    ]

    with pytest.raises(cpm_engine.CycleDetectedError) as exc_info:
        cpm_engine.calculate_cpm(activities)

    assert "Circular dependency detected" in str(exc_info.value)
    # The cycle names list should contain all 3 tasks in the cycle loop
    assert len(exc_info.value.cycle_names) >= 3
    assert "Task A" in exc_info.value.cycle_names
    assert "Task B" in exc_info.value.cycle_names
    assert "Task C" in exc_info.value.cycle_names


def test_pert_probability():
    """
    Test Case 4: Hand-computed PERT scenario
    A: opt=2, likely=4, pess=6 -> expected = 4.0, var = 0.4444...
    B: opt=3, likely=5, pess=7 -> expected = 5.0, var = 0.4444... (pred A)
    C: opt=1, likely=2, pess=3 -> expected = 2.0, var = 0.1111... (pred A)
    D: opt=2, likely=3, pess=4 -> expected = 3.0, var = 0.1111... (pred B, C)
    
    Critical path: A -> B -> D (length = 12.0)
    Project variance: Var(A) + Var(B) + Var(D) = 4/9 + 4/9 + 1/9 = 9/9 = 1.0
    With target_time = 13.0: Z = (13 - 12) / sqrt(1.0) = 1.0
    Probability of completion: norm.cdf(1.0) = 84.13%
    """
    activities = [
        {"id": "A", "name": "A", "optimistic_time": 2.0, "most_likely_time": 4.0, "pessimistic_time": 6.0, "predecessor_ids": []},
        {"id": "B", "name": "B", "optimistic_time": 3.0, "most_likely_time": 5.0, "pessimistic_time": 7.0, "predecessor_ids": ["A"]},
        {"id": "C", "name": "C", "optimistic_time": 1.0, "most_likely_time": 2.0, "pessimistic_time": 3.0, "predecessor_ids": ["A"]},
        {"id": "D", "name": "D", "optimistic_time": 2.0, "most_likely_time": 3.0, "pessimistic_time": 4.0, "predecessor_ids": ["B", "C"]}
    ]

    nodes, critical_path, expected_duration, variance, probability = cpm_engine.calculate_pert(
        activities, target_time=13.0
    )

    assert expected_duration == 12.0
    assert critical_path == ["A", "B", "D"]
    assert pytest.approx(variance, abs=1e-5) == 1.0
    assert pytest.approx(probability, abs=1e-4) == 0.8413
