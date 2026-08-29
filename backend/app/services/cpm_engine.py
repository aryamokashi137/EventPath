import math
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field

class CycleDetectedError(Exception):
    """Exception raised when a circular dependency is detected in the activity network."""
    def __init__(self, cycle_ids: List[str], cycle_names: List[str]):
        self.cycle_ids = cycle_ids
        self.cycle_names = cycle_names
        message = f"Circular dependency detected: {' -> '.join(cycle_names)}"
        super().__init__(message)


@dataclass
class ActivityNode:
    id: str
    name: str
    duration: float
    predecessors: Set[str] = field(default_factory=set)
    successors: Set[str] = field(default_factory=set)
    es: float = 0.0
    ef: float = 0.0
    ls: float = 0.0
    lf: float = 0.0
    slack: float = 0.0  # slack (total float) = LS - ES
    total_float: float = 0.0
    free_float: float = 0.0
    interfering_float: float = 0.0
    is_critical: bool = False
    
    # PERT specific calculations (only stored if computed)
    expected_time: Optional[float] = None
    variance: Optional[float] = None


def detect_cycles_and_sort(
    nodes: Dict[str, ActivityNode]
) -> Tuple[List[str], List[str]]:
    """
    Detect cycles in the network and return the topological sort order of the node IDs.
    If a cycle is detected, raises CycleDetectedError with the list of activity names.
    We use DFS with three-color marking (0: white/unvisited, 1: gray/visiting, 2: black/visited).
    """
    visited = {node_id: 0 for node_id in nodes}
    parent = {}
    temp_stack = []

    def dfs(u: str) -> List[str]:
        visited[u] = 1  # visiting
        temp_stack.append(u)
        for v in nodes[u].successors:
            if visited[v] == 1:
                # Cycle detected!
                # Reconstruct the cycle starting and ending at v
                cycle_path = []
                # Find the index of v in the stack
                try:
                    idx = temp_stack.index(v)
                    cycle_path = temp_stack[idx:] + [v]
                except ValueError:
                    cycle_path = [v, u, v]
                return cycle_path
            elif visited[v] == 0:
                parent[v] = u
                cycle = dfs(v)
                if cycle:
                    return cycle
        temp_stack.pop()
        visited[u] = 2  # visited
        return []

    # Check each node
    for node_id in nodes:
        if visited[node_id] == 0:
            cycle = dfs(node_id)
            if cycle:
                # Map IDs to names for readability
                cycle_names = [nodes[cid].name for cid in cycle]
                raise CycleDetectedError(cycle, cycle_names)

    # Kahn's algorithm or simple in-degree based topological sort for Fulkerson numbering
    # This also guarantees that every edge goes from a lower-numbered to a higher-numbered node
    in_degree = {node_id: 0 for node_id in nodes}
    for node_id, node in nodes.items():
        for succ in node.successors:
            in_degree[succ] += 1

    # Queue of nodes with no predecessors
    queue = [node_id for node_id in nodes if in_degree[node_id] == 0]
    # Keep queue sorted for deterministic results (e.g. START first, then alphabetically or by ID)
    queue.sort(key=lambda x: (x != "START", x))

    topo_order = []
    while queue:
        u = queue.pop(0)
        topo_order.append(u)
        for v in nodes[u].successors:
            in_degree[v] -= 1
            if in_degree[v] == 0:
                queue.append(v)
                # Keep queue deterministic
                queue.sort(key=lambda x: (x != "START", x == "END", x))

    return topo_order


def build_network(
    activities: List[Dict], duration_key: str = "duration"
) -> Dict[str, ActivityNode]:
    """
    Builds the ActivityNode network including virtual START and END nodes.
    `duration_key` allows specifying whether to use 'duration' or 'expected_time'.
    """
    nodes: Dict[str, ActivityNode] = {}
    
    # 1. Create nodes for all activities
    for act in activities:
        node_id = str(act["id"])
        nodes[node_id] = ActivityNode(
            id=node_id,
            name=act["name"],
            duration=float(act[duration_key]),
            expected_time=act.get("expected_time"),
            variance=act.get("variance")
        )

    # 2. Add predecessors and successors
    for act in activities:
        node_id = str(act["id"])
        pred_ids = act.get("predecessor_ids", [])
        for p_id in pred_ids:
            p_id_str = str(p_id)
            if p_id_str not in nodes:
                raise ValueError(f"Predecessor activity with ID {p_id_str} not found in the project.")
            nodes[node_id].predecessors.add(p_id_str)
            nodes[p_id_str].successors.add(node_id)

    # 3. Create virtual START and END nodes
    start_node = ActivityNode(id="START", name="Start", duration=0.0)
    end_node = ActivityNode(id="END", name="End", duration=0.0)
    
    nodes["START"] = start_node
    nodes["END"] = end_node

    # Connect START to nodes with no user-defined predecessors
    for node_id, node in list(nodes.items()):
        if node_id in ("START", "END"):
            continue
        if not node.predecessors:
            node.predecessors.add("START")
            start_node.successors.add(node_id)

    # Connect nodes with no successors to END
    for node_id, node in list(nodes.items()):
        if node_id in ("START", "END"):
            continue
        if not node.successors:
            node.successors.add("END")
            end_node.predecessors.add(node_id)

    # Special case: empty project
    if len(nodes) == 2:
        start_node.successors.add("END")
        end_node.predecessors.add("START")

    return nodes


def run_cpm_passes(
    nodes: Dict[str, ActivityNode], topo_order: List[str]
) -> List[str]:
    """
    Executes forward and backward passes.
    Returns the critical path as a sequence of activity IDs from START to END.
    """
    # 1. Forward Pass: Earliest Start (ES) and Earliest Finish (EF)
    for node_id in topo_order:
        node = nodes[node_id]
        if node_id == "START":
            node.es = 0.0
            node.ef = 0.0
        else:
            node.es = max(nodes[p_id].ef for p_id in node.predecessors)
            node.ef = node.es + node.duration

    # Project duration is EF of END node
    project_duration = nodes["END"].ef

    # 2. Backward Pass: Latest Finish (LF) and Latest Start (LS)
    for node_id in reversed(topo_order):
        node = nodes[node_id]
        if node_id == "END":
            node.lf = project_duration
            node.ls = project_duration
        else:
            node.lf = min(nodes[s_id].ls for s_id in node.successors)
            node.ls = node.lf - node.duration

    # 3. Calculate float/slack and determine if critical
    # We use a small epsilon for float comparison to handle floating point precision
    eps = 1e-9
    for node_id, node in nodes.items():
        node.slack = node.ls - node.es
        if abs(node.slack) < eps:
            node.slack = 0.0
        node.total_float = node.slack
        node.is_critical = abs(node.slack) < eps

        # Calculate Free Float: min(ES of successors) - EF of current node
        if node.successors:
            min_succ_es = min(nodes[s_id].es for s_id in node.successors)
            node.free_float = min_succ_es - node.ef
        else:
            node.free_float = node.total_float

        if abs(node.free_float) < eps:
            node.free_float = 0.0

        node.interfering_float = max(0.0, node.total_float - node.free_float)
        if abs(node.interfering_float) < eps:
            node.interfering_float = 0.0

    # 4. Construct a sequential critical path from START to END
    # A path is a sequence of zero-slack nodes starting at START and ending at END
    critical_path = ["START"]
    curr = "START"
    topo_indices = {node_id: idx for idx, node_id in enumerate(topo_order)}
    
    while curr != "END":
        # Find a successor of curr that is critical and starts when curr finishes
        next_nodes = [
            s_id for s_id in nodes[curr].successors
            if nodes[s_id].is_critical and abs(nodes[s_id].es - nodes[curr].ef) < eps
        ]
        if not next_nodes:
            break
        # Sort by topological order to make traversal deterministic
        next_nodes.sort(key=lambda x: topo_indices[x])
        curr = next_nodes[0]
        critical_path.append(curr)

    # Return only actual activity IDs (exclude START and END from the final list,
    # but keep them if requested. Usually, the user wants the activity ids.
    # We will exclude 'START' and 'END' to return only the project's activities,
    # but the internal representation can retain them.)
    return [cid for cid in critical_path if cid not in ("START", "END")]


def calculate_cpm(activities: List[Dict]) -> Tuple[Dict[str, ActivityNode], List[str], float]:
    """
    Core function for Critical Path Method calculation.
    """
    nodes = build_network(activities, duration_key="duration")
    topo_order = detect_cycles_and_sort(nodes)
    critical_path = run_cpm_passes(nodes, topo_order)
    project_duration = nodes["END"].ef
    return nodes, critical_path, project_duration


def calculate_pert(
    activities: List[Dict], target_time: Optional[float] = None
) -> Tuple[Dict[str, ActivityNode], List[str], float, float, Optional[float]]:
    """
    Core function for PERT calculations.
    Computes expected durations and variances for each activity.
    Runs CPM using expected duration.
    Calculates project variance (sum of variances of activities on the critical path).
    If target_time is provided, calculates probability of on-time completion.
    """
    # 1. Precalculate expected time and variance for each activity
    pert_activities = []
    for act in activities:
        opt = float(act["optimistic_time"])
        lk = float(act["most_likely_time"])
        pes = float(act["pessimistic_time"])
        
        expected = (opt + 4.0 * lk + pes) / 6.0
        variance = ((pes - opt) / 6.0) ** 2
        
        # Clone activity dict and update duration
        act_copy = act.copy()
        act_copy["duration"] = expected
        act_copy["expected_time"] = expected
        act_copy["variance"] = variance
        pert_activities.append(act_copy)

    # 2. Run CPM using expected times as duration
    nodes, critical_path, expected_duration = calculate_cpm(pert_activities)

    # 3. Sum variance of activities ON the critical path
    # Note: we only sum variances of activities that are in the critical path sequence.
    # Exclude virtual START and END nodes since their variance is 0 (or not set).
    project_variance = 0.0
    for node_id in critical_path:
        if node_id in nodes and nodes[node_id].variance is not None:
            project_variance += nodes[node_id].variance

    # 4. Calculate probability of completion before target_time
    probability = None
    if target_time is not None:
        if project_variance <= 1e-12:
            # If variance is 0, probability is 1.0 if target_time >= expected_duration, else 0.0
            probability = 1.0 if target_time >= expected_duration else 0.0
        else:
            std_dev = math.sqrt(project_variance)
            z = (target_time - expected_duration) / std_dev
            # We will use scipy.stats.norm.cdf(z) in the service layer, or we can use math.erf here to keep it scipy-independent.
            # Wait, the prompt says: "return probability of on-time completion using scipy.stats.norm.cdf(Z) (scipy is fine as a dependency for this)"
            # Let's import scipy here or import it locally so if scipy is not installed yet it doesn't fail import.
            try:
                from scipy.stats import norm
                probability = float(norm.cdf(z))
            except ImportError:
                # Fallback mathematical approximation of standard normal CDF using error function
                probability = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))

    return nodes, critical_path, expected_duration, project_variance, probability


def crash_project_network(
    activities: List[Dict],
    target_duration: Optional[float] = None,
    max_budget: Optional[float] = None
) -> Dict:
    """
    Gap 2: Crashing Optimization Engine.
    Iteratively crashes activities on the critical path with the lowest cost per day
    until target duration or max budget is satisfied or no further crashing is possible.
    """

    acts_map = {}
    baseline_cost = 0.0

    for act in activities:
        aid = str(act["id"])

        # Use stored duration when available.
        # For PERT projects, duration may be 0, so calculate
        # the PERT expected duration.
        norm_dur = float(act.get("duration") or 0.0)

        if norm_dur <= 0:
            opt = act.get("optimistic_time")
            most_likely = act.get("most_likely_time")
            pess = act.get("pessimistic_time")

            if (
                opt is not None
                and most_likely is not None
                and pess is not None
            ):
                norm_dur = (
                    float(opt)
                    + 4 * float(most_likely)
                    + float(pess)
                ) / 6.0

        crash_dur_value = act.get("crash_duration")

        if crash_dur_value is not None:
            crash_dur = min(
                float(crash_dur_value),
                norm_dur
            )
        else:
            crash_dur = norm_dur

        norm_cost = (
            float(act.get("normal_cost"))
            if act.get("normal_cost") is not None
            else 0.0
        )

        crash_cost = (
            float(act.get("crash_cost"))
            if act.get("crash_cost") is not None
            else norm_cost
        )

        max_crashable = norm_dur - crash_dur

        cost_per_day = (
            (crash_cost - norm_cost) / max_crashable
            if max_crashable > 1e-6
            else float("inf")
        )

        if cost_per_day < 0:
            cost_per_day = 0.0

        acts_map[aid] = {
            "id": aid,
            "name": act["name"],
            "duration": norm_dur,
            "original_duration": norm_dur,
            "crash_duration": crash_dur,
            "normal_cost": norm_cost,
            "crash_cost": crash_cost,
            "cost_per_day": cost_per_day,
            "days_crashed": 0.0,
            "predecessor_ids": act.get("predecessor_ids", [])
        }

        baseline_cost += norm_cost

    # Baseline CPM
    initial_acts = [v.copy() for v in acts_map.values()]
    _, init_cp, orig_duration = calculate_cpm(initial_acts)

    current_duration = orig_duration
    accumulated_crash_cost = 0.0

    # Iterative crashing loop
    step = 1.0
    max_iterations = 500
    iteration = 0

    while iteration < max_iterations:
        iteration += 1

        if (
            target_duration is not None
            and current_duration <= target_duration + 1e-6
        ):
            break

        curr_acts_list = [
            {
                "id": v["id"],
                "name": v["name"],
                "duration": v["duration"],
                "predecessor_ids": v["predecessor_ids"]
            }
            for v in acts_map.values()
        ]

        _, curr_cp, curr_dur = calculate_cpm(curr_acts_list)
        current_duration = curr_dur

        if (
            target_duration is not None
            and current_duration <= target_duration + 1e-6
        ):
            break

        candidates = []

        for aid in curr_cp:
            node = acts_map.get(aid)

            if (
                node
                and node["duration"] > node["crash_duration"] + 1e-6
                and node["cost_per_day"] < float("inf")
            ):
                candidates.append(node)

        if not candidates:
            break

        best_candidate = min(
            candidates,
            key=lambda x: x["cost_per_day"]
        )

        possible_reduction = (
            best_candidate["duration"]
            - best_candidate["crash_duration"]
        )

        actual_step = min(step, possible_reduction)

        if target_duration is not None:
            actual_step = min(
                actual_step,
                current_duration - target_duration
            )

        additional_cost = (
            actual_step
            * best_candidate["cost_per_day"]
        )

        if (
            max_budget is not None
            and accumulated_crash_cost + additional_cost
            > max_budget + 1e-6
        ):
            remaining_budget = (
                max_budget - accumulated_crash_cost
            )

            if (
                remaining_budget > 1e-6
                and best_candidate["cost_per_day"] > 0
            ):
                actual_step = min(
                    remaining_budget
                    / best_candidate["cost_per_day"],
                    possible_reduction
                )

                additional_cost = (
                    actual_step
                    * best_candidate["cost_per_day"]
                )
            else:
                break

        if actual_step <= 1e-6:
            break

        best_candidate["duration"] -= actual_step
        best_candidate["days_crashed"] += actual_step
        accumulated_crash_cost += additional_cost

    # Final CPM
    final_acts_list = [
        {
            "id": v["id"],
            "name": v["name"],
            "duration": v["duration"],
            "predecessor_ids": v["predecessor_ids"]
        }
        for v in acts_map.values()
    ]

    _, final_cp, final_duration = calculate_cpm(final_acts_list)

    crashed_details = []

    for aid, node in acts_map.items():
        if node["days_crashed"] > 1e-6:
            crashed_details.append({
                "activity_id": aid,
                "activity_name": node["name"],
                "original_duration": node["original_duration"],
                "crashed_duration": node["duration"],
                "days_crashed": round(node["days_crashed"], 2),
                "cost_per_day": round(node["cost_per_day"], 2),
                "total_crash_cost": round(
                    node["days_crashed"]
                    * node["cost_per_day"],
                    2
                )
            })

    return {
        "original_duration": round(orig_duration, 2),
        "crashed_duration": round(final_duration, 2),
        "total_days_saved": round(
            orig_duration - final_duration,
            2
        ),
        "baseline_cost": round(baseline_cost, 2),
        "additional_crash_cost": round(
            accumulated_crash_cost, 2
        ),
        "final_total_cost": round(
            baseline_cost + accumulated_crash_cost,
            2
        ),
        "crashed_activities": crashed_details,
        "final_critical_path": final_cp
    }


def run_monte_carlo_simulation(
    activities: List[Dict],
    num_simulations: int = 1000,
    target_time: Optional[float] = None
) -> Dict:
    """
    Gap 3: Probabilistic PERT Monte Carlo Simulation & S-Curve Risk Analysis Engine.
    Executes random sampling over PERT 3-point estimates to quantify merge-event bias,
    activity criticality indices, percentiles, and cumulative probability S-curves.
    """
    import random

    valid_activities = []
    for act in activities:
        opt = float(act["optimistic_time"]) if act.get("optimistic_time") is not None else float(act.get("duration", 1.0))
        lk = float(act["most_likely_time"]) if act.get("most_likely_time") is not None else opt
        pes = float(act["pessimistic_time"]) if act.get("pessimistic_time") is not None else lk
        
        # Ensure opt <= lk <= pes
        opt_val = min(opt, lk, pes)
        pes_val = max(opt, lk, pes)
        lk_val = lk
        if not (opt_val <= lk_val <= pes_val):
            lk_val = opt_val

        valid_activities.append({
            "id": str(act["id"]),
            "name": act["name"],
            "opt": opt_val,
            "lk": lk_val,
            "pes": pes_val,
            "predecessor_ids": act.get("predecessor_ids", [])
        })

    durations = []
    critical_counts = {act["id"]: 0 for act in valid_activities}

    for _ in range(num_simulations):
        sampled_acts = []
        for act in valid_activities:
            if abs(act["pes"] - act["opt"]) < 1e-6:
                sample_dur = act["lk"]
            else:
                sample_dur = random.triangular(act["opt"], act["pes"], act["lk"])
            
            sampled_acts.append({
                "id": act["id"],
                "name": act["name"],
                "duration": sample_dur,
                "predecessor_ids": act["predecessor_ids"]
            })
        
        nodes, critical_path, proj_dur = calculate_cpm(sampled_acts)
        durations.append(proj_dur)
        for cid in critical_path:
            if cid in critical_counts:
                critical_counts[cid] += 1

    durations.sort()
    n = len(durations)

    mean_dur = sum(durations) / n
    variance = sum((x - mean_dur) ** 2 for x in durations) / n
    std_dev = math.sqrt(variance)

    def percentile(p):
        idx = int(p * (n - 1))
        return durations[idx]

    p10 = percentile(0.10)
    p50 = percentile(0.50)
    p80 = percentile(0.80)
    p90 = percentile(0.90)
    p95 = percentile(0.95)

    empirical_prob = None
    if target_time is not None:
        on_time_count = sum(1 for d in durations if d <= target_time)
        empirical_prob = round(on_time_count / n, 4)

    criticality_indices = []
    for act in valid_activities:
        pct = round((critical_counts[act["id"]] / n) * 100.0, 2)
        criticality_indices.append({
            "activity_id": act["id"],
            "activity_name": act["name"],
            "criticality_percentage": pct
        })

    # Generate 50 representative data points for S-Curve plot
    step_idx = max(1, n // 50)
    s_curve = []
    for i in range(0, n, step_idx):
        dur = round(durations[i], 2)
        cum_p = round((i + 1) / n, 4)
        s_curve.append({"duration": dur, "cumulative_probability": cum_p})

    if s_curve[-1]["duration"] != round(durations[-1], 2):
        s_curve.append({"duration": round(durations[-1], 2), "cumulative_probability": 1.0})

    return {
        "num_simulations": n,
        "mean_duration": round(mean_dur, 2),
        "std_dev_duration": round(std_dev, 2),
        "min_duration": round(durations[0], 2),
        "max_duration": round(durations[-1], 2),
        "p10": round(p10, 2),
        "p50": round(p50, 2),
        "p80": round(p80, 2),
        "p90": round(p90, 2),
        "p95": round(p95, 2),
        "empirical_probability": empirical_prob,
        "criticality_indices": criticality_indices,
        "s_curve": s_curve
    }


