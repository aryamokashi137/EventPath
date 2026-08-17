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
    slack: float = 0.0  # slack (or float) = LS - ES
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
        # Clean up negative zeros or extremely small floating numbers
        if abs(node.slack) < eps:
            node.slack = 0.0
        node.is_critical = abs(node.slack) < eps

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
