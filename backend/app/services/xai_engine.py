"""Explainable AI (XAI) reasoning layer for EventPath scheduling analytics.

This module converts raw Operations Research outputs into structured,
evidence-traced natural language explanations:

* CPM forward/backward pass metrics (ES/EF/LS/LF, total float, free float)
* PERT expected durations, variance, standard deviation and Z-scores
* Monte Carlo activity criticality indices and path statistics
* Schedule crashing cost-per-day slopes
* Vendor calendar collisions and overbooking overlaps

Every function is pure: it accepts already-computed metrics and returns
plain dictionaries. There are no database or HTTP concerns, which keeps the
explanation layer independently unit testable and fully reproducible.
"""

import math
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.services import cpm_engine


EPS = 1e-9
VIRTUAL_NODES = ("START", "END")

SEVERITY_CRITICAL = "CRITICAL"
SEVERITY_WARNING = "WARNING"
SEVERITY_INFO = "INFO"
SEVERITY_SUCCESS = "SUCCESS"

REPORT_CRITICAL_PATH = "CRITICAL_PATH_FLOAT"
REPORT_RISK = "PROBABILISTIC_RISK"
REPORT_CRASHING = "COUNTERFACTUAL_CRASHING"
REPORT_VENDOR = "VENDOR_CONFLICTS"

DEFAULT_MERGE_EVENT_BIAS_THRESHOLD = 0.20
DEFAULT_NEAR_CRITICAL_THRESHOLD = 0.30
DEFAULT_CRITICALITY_INDEX_THRESHOLD = 0.30
NEAR_CRITICAL_ABSOLUTE_DAYS = 2.0
NEAR_CRITICAL_RATIO = 0.10
MERGE_MIN_COMBINED_SD = 0.5
MERGE_MAX_GAP_DAYS = 3.0
MAX_ENUMERATED_PATHS = 512
MAX_CRASH_COUNTERFACTUALS = 3


# ---------------------------------------------------------------------------
# Numeric formatting helpers
# ---------------------------------------------------------------------------

def _days(value: Optional[float], digits: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.{digits}f} days"


def _money(value: Optional[float]) -> str:
    if value is None or math.isinf(value):
        return "unbounded"
    return f"${float(value):,.2f}"


def _percent(value: Optional[float], digits: int = 1) -> str:
    if value is None:
        return "n/a"
    return f"{float(value) * 100:.{digits}f}%"


def _iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat()


# ---------------------------------------------------------------------------
# Distribution helpers
# ---------------------------------------------------------------------------

def _normal_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def standard_normal_cdf(z: float) -> float:
    """Cumulative distribution function of the standard normal distribution."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def merge_event_bias_days(mean_gap: float, combined_sigma: float) -> float:
    """Expected overshoot of a merge event above the longest branch mean.

    For two branches with means m1 >= m2 and combined standard deviation
    sigma, E[max(X, Y)] - m1 = sigma * phi(d) - d * (1 - Phi(d)) where
    d = |m1 - m2| / sigma. This is the PERT "merge bias" term: a merge event
    is systematically longer than the CPM path that feeds it, even when both
    activities are individually close to their expected durations.
    """
    if combined_sigma <= EPS:
        return 0.0
    d = abs(mean_gap) / combined_sigma
    return combined_sigma * _normal_pdf(d) - abs(mean_gap) * (1.0 - standard_normal_cdf(d))


# ---------------------------------------------------------------------------
# Network introspection helpers
# ---------------------------------------------------------------------------

def _real_nodes(nodes: Dict[str, cpm_engine.ActivityNode]) -> Dict[str, cpm_engine.ActivityNode]:
    return {k: v for k, v in nodes.items() if k not in VIRTUAL_NODES}


def _name_of(nodes: Dict[str, cpm_engine.ActivityNode], node_id: str) -> str:
    if node_id == "START":
        return "Project start"
    if node_id == "END":
        return "Project finish"
    node = nodes.get(node_id)
    return node.name if node is not None else node_id


def _required_es(predecessor: cpm_engine.ActivityNode,
                 node: cpm_engine.ActivityNode,
                 spec: Dict[str, Any]) -> float:
    dep_type = spec.get("dependency_type", "FS")
    lag = float(spec.get("lag", 0.0) or 0.0)
    if dep_type == "SS":
        return predecessor.es + lag
    if dep_type == "FF":
        return predecessor.ef + lag - node.duration
    if dep_type == "SF":
        return predecessor.es + lag - node.duration
    return predecessor.ef + lag


def _required_lf(successor: cpm_engine.ActivityNode,
                 node: cpm_engine.ActivityNode,
                 spec: Dict[str, Any]) -> float:
    dep_type = spec.get("dependency_type", "FS")
    lag = float(spec.get("lag", 0.0) or 0.0)
    if dep_type == "SS":
        return successor.ls - lag + node.duration
    if dep_type == "FF":
        return successor.lf - lag
    if dep_type == "SF":
        return successor.lf - lag + node.duration
    return successor.ls - lag


def _earliest_start_driver(nodes: Dict[str, cpm_engine.ActivityNode],
                           node: cpm_engine.ActivityNode) -> Optional[Dict[str, Any]]:
    """Identify which predecessor actually pinned this activity's ES."""
    best_spec = None
    best_required = None
    for spec in node.predecessor_specs:
        predecessor = nodes.get(spec.get("pred_id"))
        if predecessor is None:
            continue
        required = _required_es(predecessor, node, spec)
        if best_required is None or required > best_required:
            best_required = required
            best_spec = spec
    if best_spec is None:
        return None
    return {
        "activity_id": best_spec.get("pred_id"),
        "activity_name": _name_of(nodes, best_spec.get("pred_id")),
        "dependency_type": best_spec.get("dependency_type", "FS"),
        "lag": float(best_spec.get("lag", 0.0) or 0.0),
        "required_start": best_required,
    }


def _latest_finish_driver(nodes: Dict[str, cpm_engine.ActivityNode],
                          node: cpm_engine.ActivityNode) -> Optional[Dict[str, Any]]:
    """Identify which successor consumed this activity's slack."""
    best_spec = None
    best_required = None
    for spec in node.successor_specs:
        successor = nodes.get(spec.get("succ_id"))
        if successor is None:
            continue
        required = _required_lf(successor, node, spec)
        if best_required is None or required < best_required:
            best_required = required
            best_spec = spec
    if best_spec is None:
        return None
    return {
        "activity_id": best_spec.get("succ_id"),
        "activity_name": _name_of(nodes, best_spec.get("succ_id")),
        "dependency_type": best_spec.get("dependency_type", "FS"),
        "lag": float(best_spec.get("lag", 0.0) or 0.0),
        "required_finish": best_required,
    }


def enumerate_network_paths(nodes: Dict[str, cpm_engine.ActivityNode],
                            max_paths: int = MAX_ENUMERATED_PATHS
                            ) -> List[List[str]]:
    """Enumerate every distinct START-to-END route through the activity network."""
    paths: List[List[str]] = []

    def walk(node_id: str, trail: List[str], visited: set) -> None:
        if len(paths) >= max_paths:
            return
        if node_id == "END":
            paths.append([p for p in trail if p not in VIRTUAL_NODES])
            return
        successor_specs = nodes[node_id].successor_specs
        if successor_specs:
            candidates = [s.get("succ_id") for s in successor_specs]
        else:
            candidates = sorted(nodes[node_id].successors)
        for candidate in candidates:
            if candidate is None or candidate in visited or candidate not in nodes:
                continue
            visited.add(candidate)
            trail.append(candidate)
            walk(candidate, trail, visited)
            trail.pop()
            visited.discard(candidate)

    if "START" in nodes and "END" in nodes:
        walk("START", ["START"], {"START"})
    return paths


def _path_records(nodes: Dict[str, cpm_engine.ActivityNode]) -> List[Dict[str, Any]]:
    seen = set()
    records: List[Dict[str, Any]] = []
    for activity_ids in enumerate_network_paths(nodes):
        if not activity_ids:
            continue
        key = tuple(activity_ids)
        if key in seen:
            continue
        seen.add(key)
        members = [nodes[a] for a in activity_ids]
        records.append({
            "activity_ids": list(activity_ids),
            "activity_names": [n.name for n in members],
            "length": sum(n.duration for n in members),
            "path_float": min(n.total_float for n in members),
            "variance": sum((n.variance or 0.0) for n in members),
        })
    records.sort(key=lambda r: r["length"], reverse=True)
    return records


def _branch_correlation(nodes: Dict[str, cpm_engine.ActivityNode],
                       left: str, right: str) -> float:
    """Heuristic correlation of two parallel branches feeding a merge."""
    left_node = nodes.get(left)
    right_node = nodes.get(right)
    if left_node is None or right_node is None:
        return 0.0
    if right in left_node.successors or left in right_node.successors:
        return 0.5
    if set(left_node.predecessors) & set(right_node.predecessors):
        return 0.5
    return 0.0


# ---------------------------------------------------------------------------
# Structured explanation primitives
# ---------------------------------------------------------------------------

def _evidence(pairs: Sequence[Tuple[str, Any]]) -> List[Dict[str, str]]:
    return [{"label": label, "value": str(value)} for label, value in pairs if value is not None]


def _action(action: str, rationale: str, priority: str = "MEDIUM",
            metric: Optional[str] = None) -> Dict[str, str]:
    return {
        "priority": priority,
        "action": action,
        "rationale": rationale,
        "metric": metric or "",
    }


def _card(severity: str, kind: str, title: str, narrative: str,
          evidence: Optional[List[Dict[str, str]]] = None,
          actions: Optional[List[Dict[str, str]]] = None,
          activity_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "severity": severity,
        "kind": kind,
        "title": title,
        "narrative": narrative,
        "evidence": evidence or [],
        "actions": actions or [],
        "activity_ids": activity_ids or [],
    }


def _highest_severity(cards: Sequence[Dict[str, Any]]) -> str:
    order = [SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_SUCCESS, SEVERITY_INFO]
    present = {card.get("severity") for card in cards}
    for level in order:
        if level in present:
            return level
    return SEVERITY_INFO


def _report(report_type: str, title: str, headline: Dict[str, str],
            summary: str, narrative: List[str], cards: List[Dict[str, Any]],
            metrics: Dict[str, Any], evidence_trace: List[Dict[str, Any]],
            confidence: Dict[str, str]) -> Dict[str, Any]:
    recommended_actions: List[Dict[str, str]] = []
    high_risk: List[str] = []
    for card in cards:
        for item in card.get("actions", []):
            if item not in recommended_actions:
                recommended_actions.append(item)
        if card.get("severity") == SEVERITY_CRITICAL:
            high_risk.append(card.get("title", ""))

    return {
        "report_type": report_type,
        "title": title,
        "headline": headline,
        "summary": summary,
        "narrative": narrative,
        "cards": cards,
        "severity": _highest_severity(cards),
        "high_risk_findings": high_risk,
        "recommended_actions": recommended_actions,
        "metrics": metrics,
        "evidence_trace": evidence_trace,
        "confidence": confidence,
    }


def _join_names(names: Sequence[str], limit: int = 3) -> str:
    cleaned = [n for n in names if n]
    if not cleaned:
        return "none"
    if len(cleaned) <= limit:
        return " -> ".join(cleaned)
    return " -> ".join(cleaned[:limit]) + f" -> (+{len(cleaned) - limit} more)"


# ---------------------------------------------------------------------------
# (a) Critical path and float explanation
# ---------------------------------------------------------------------------

def explain_critical_path_and_float(
    nodes: Dict[str, cpm_engine.ActivityNode],
    critical_path: Sequence[str],
    project_duration: float,
    project_name: Optional[str] = None,
    mode: str = "CPM",
) -> Dict[str, Any]:
    """Explain the dominant bottlenecks, zero-float tasks and buffer distribution.

    Args:
        nodes: Output of ``cpm_engine.build_network`` after
            ``run_cpm_passes`` (ES/EF/LS/LF and float metrics populated).
        critical_path: Activity ids forming the zero-float chain.
        project_duration: EF of the virtual END node.
        project_name: Optional project label used in the narrative.
        mode: ``CPM`` or ``PERT``; only affects wording, never the math.
    """
    real = _real_nodes(nodes)
    critical_ids = [cid for cid in critical_path if cid in real]
    critical_set = set(critical_ids)
    non_critical = {k: v for k, v in real.items() if k not in critical_set}
    label = project_name or "this project"

    cards: List[Dict[str, Any]] = []
    near_critical_threshold = max(NEAR_CRITICAL_ABSOLUTE_DAYS,
                                  project_duration * NEAR_CRITICAL_RATIO)

    for activity_id in critical_ids:
        node = nodes[activity_id]
        start_driver = _earliest_start_driver(nodes, node)
        finish_driver = _latest_finish_driver(nodes, node)
        tail_exposure = max(0.0, project_duration - node.ef)

        if start_driver is None:
            cause = "It is an entry point of the network and therefore starts at day zero."
        else:
            cause = (f"Its earliest start of {_days(node.es)} is dictated by "
                     f"'{start_driver['activity_name']}'"
                     f"{' with a ' + str(start_driver['dependency_type']) + ' relationship' if start_driver['dependency_type'] != 'FS' else ''}"
                     f" and cannot be pulled forward.")

        successor_clause = ""
        if finish_driver is not None and finish_driver["activity_id"] not in VIRTUAL_NODES:
            successor_clause = (f" It in turn pins the earliest start of "
                                f"'{finish_driver['activity_name']}', so the delay propagates forward.")
        else:
            successor_clause = " It is the final deliverable, so the delay lands directly on the event date."

        narrative = (
            f"'{node.name}' has a duration of {_days(node.duration)} and zero total float "
            f"(ES {_days(node.es)} / EF {_days(node.ef)} / LS {_days(node.ls)} / LF {_days(node.lf)}). "
            f"{cause}{successor_clause} A slip of one day on this activity delays the whole event by one day."
        )

        cards.append(_card(
            SEVERITY_CRITICAL,
            "ZERO_FLOAT_BOTTLENECK",
            f"Bottleneck: {node.name}",
            narrative,
            evidence=_evidence([
                ("Duration", _days(node.duration)),
                ("ES / EF", f"{node.es:.2f} / {node.ef:.2f}"),
                ("LS / LF", f"{node.ls:.2f} / {node.lf:.2f}"),
                ("Total float", "0.00 days"),
                ("Driven by", start_driver["activity_name"] if start_driver else "Project start"),
                ("Driving", finish_driver["activity_name"] if finish_driver else "Project finish"),
                ("Downstream exposure", _days(tail_exposure)),
            ]),
            actions=[_action(
                f"Protect '{node.name}' as a zero-float priority task.",
                "Any delay here is a one-for-one delay to the event date because total float is exhausted.",
                "HIGH",
                "0.00 days float",
            )],
            activity_ids=[activity_id],
        ))

    free_float_pool = sum(n.free_float for n in non_critical.values())
    gross_total_float = sum(n.total_float for n in non_critical.values())
    usable = sorted(
        [n for n in non_critical.values() if n.free_float > EPS],
        key=lambda n: n.free_float,
        reverse=True,
    )
    trapped = sorted(
        [n for n in non_critical.values() if n.total_float > EPS and n.free_float <= EPS],
        key=lambda n: n.total_float,
        reverse=True,
    )

    for node in usable[:5]:
        cards.append(_card(
            SEVERITY_INFO,
            "FREE_FLOAT_BUFFER",
            f"Buffer: {node.name}",
            (f"'{node.name}' carries {_days(node.free_float)} of free float, meaning it can absorb that much "
             f"delay without disturbing any downstream activity. It is the cheapest available shock absorber "
             f"if a predecessor overruns."),
            evidence=_evidence([
                ("Free float", _days(node.free_float)),
                ("Total float", _days(node.total_float)),
                ("Interfering float", _days(node.interfering_float)),
                ("ES / EF", f"{node.es:.2f} / {node.ef:.2f}"),
            ]),
            activity_ids=[node.id],
        ))

    for node in trapped[:3]:
        cards.append(_card(
            SEVERITY_WARNING,
            "STRUCTURAL_FLOAT",
            f"Trapped float: {node.name}",
            (f"'{node.name}' shows {_days(node.total_float)} of total float but zero free float. That float is "
             f"structural, not usable: it only materialises if the following activity also slips, so it cannot be "
             f"treated as contingency time."),
            evidence=_evidence([
                ("Total float", _days(node.total_float)),
                ("Free float", "0.00 days"),
                ("Interfering float", _days(node.interfering_float)),
                ("Reason", "Successor starts exactly at this activity's earliest finish"),
            ]),
            actions=[_action(
                f"Do not spend the {_days(node.total_float)} reported for '{node.name}' as contingency.",
                "Free float is zero, so any overrun directly delays the successor that shares its finish.",
                "MEDIUM",
                "0.00 days free float",
            )],
            activity_ids=[node.id],
        ))

    near_critical = [
        n for n in non_critical.values() if 0.0 < n.total_float <= near_critical_threshold
    ]
    near_critical.sort(key=lambda n: n.total_float)
    for node in near_critical[:4]:
        cards.append(_card(
            SEVERITY_WARNING,
            "NEAR_CRITICAL",
            f"Near-critical: {node.name}",
            (f"'{node.name}' holds only {_days(node.total_float)} of float against a "
             f"{_days(project_duration)} schedule, which is inside the near-critical band of "
             f"{_days(near_critical_threshold)}. A slip of more than {_days(node.total_float)} promotes it onto "
             f"the critical path and lengthens the event."),
            evidence=_evidence([
                ("Total float", _days(node.total_float)),
                ("Near-critical threshold", _days(near_critical_threshold)),
                ("Duration", _days(node.duration)),
            ]),
            activity_ids=[node.id],
        ))

    path_records = _path_records(nodes)
    critical_length = path_records[0]["length"] if path_records else project_duration
    alternative_paths = [r for r in path_records if abs(r["length"] - critical_length) > EPS]
    path_cards_added = 0
    for record in alternative_paths:
        if path_cards_added >= 3:
            break
        float_gap = critical_length - record["length"]
        if float_gap > near_critical_threshold:
            continue
        path_cards_added += 1
        cards.append(_card(
            SEVERITY_WARNING,
            "FLOAT_SHIELD",
            f"Near-critical route: {_join_names(record['activity_names'], limit=2)}",
            (f"An alternative route through {_join_names(record['activity_names'], limit=4)} is only "
             f"{_days(float_gap)} shorter than the critical path. It functions as the project's real safety net: "
             f"if one critical activity slips, the event slips by that same amount because this route cannot take "
             f"over."),
            evidence=_evidence([
                ("Route length", _days(record["length"])),
                ("Critical path length", _days(critical_length)),
                ("Route float shield", _days(record["path_float"])),
                ("Gap to critical", _days(float_gap)),
            ]),
            activity_ids=record["activity_ids"],
        ))

    if not real:
        summary = (
            f"{label} has no activities yet, so there is no network to explain. The critical path is empty, every "
            f"duration metric is zero, and no float exists to allocate. Add activities and re-run the explanation to "
            f"get bottleneck, float and contingency guidance."
        )
        narrative_sentences = [
            f"{label} contains 0 activities.",
            "No critical path, float or bottleneck can be derived from an empty network.",
            "Add activities to unlock the scheduling explanations.",
        ]
    else:
        summary = (
            f"The {_days(critical_length)} critical path of {label} is {_join_names([nodes[a].name for a in critical_ids])}. "
            f"Those {len(critical_ids)} activities have zero float and therefore transfer any delay one-for-one to the "
            f"event date. The remaining {len(non_critical)} activities hold {_days(free_float_pool)} of genuinely usable "
            f"free float and {_days(gross_total_float)} of gross total float, of which only the free float can be spent "
            f"as contingency without a knock-on delay."
        )

        narrative_sentences = [
            f"Critical path ({len(critical_ids)} activities): {_join_names([nodes[a].name for a in critical_ids])}.",
            f"Zero-float bottlenecks: {len(critical_ids)}.",
            f"Usable free-float buffers: {len(usable)} activities sharing {_days(free_float_pool)}.",
            f"Trapped (structural) float: {len(trapped)} activities that report float but cannot absorb a delay alone.",
            f"Near-critical activities inside the {_days(near_critical_threshold)} band: {len(near_critical)}.",
        ]

    actions: List[Dict[str, str]] = []
    if critical_ids:
        actions.append(_action(
            f"Focus acceleration budget on '{nodes[critical_ids[0]].name}' first.",
            "It sits on the critical path, so reducing it yields the largest project-level gain per unit of cost.",
            "HIGH",
            f"{len(critical_ids)} zero-float activities",
        ))
    if usable:
        actions.append(_action(
            f"Reserve the {_days(free_float_pool)} of free float as project contingency.",
            "Free float is simultaneously available across activities and is the only float that can absorb an overrun without cascading.",
            "MEDIUM",
            _days(free_float_pool),
        ))
    if trapped:
        actions.append(_action(
            f"Re-negotiate the {len(trapped)} activities whose float is structurally trapped.",
            "Their reported float evaporates unless a successor slips, so commitments built on it are unsafe.",
            "MEDIUM",
            f"{len(trapped)} activities",
        ))

    metrics = {
        "project_duration_days": round(project_duration, 2),
        "critical_path_length_days": round(critical_length, 2),
        "activity_count": len(real),
        "critical_activity_count": len(critical_ids),
        "non_critical_activity_count": len(non_critical),
        "free_float_pool_days": round(free_float_pool, 2),
        "gross_total_float_pool_days": round(gross_total_float, 2),
        "near_critical_threshold_days": round(near_critical_threshold, 2),
        "near_critical_count": len(near_critical),
        "enumerated_path_count": len(path_records),
        "alternative_path_count": len(alternative_paths),
    }

    evidence_trace = [
        {
            "step": "Forward pass",
            "method": "ES = max over predecessors of required start; EF = ES + duration",
            "inputs": f"{len(real)} activities, dependency types FS/SS/FF/SF with lag",
        },
        {
            "step": "Backward pass",
            "method": "LF = min over successors of required finish; LS = LF - duration",
            "inputs": f"Project duration = {_days(project_duration)} (EF of the virtual END node)",
        },
        {
            "step": "Float classification",
            "method": "Total float = LS - ES; free float = min(ES of successors) - EF",
            "inputs": f"Gross total float {_days(gross_total_float)}; free float {_days(free_float_pool)}",
        },
        {
            "step": "Path enumeration",
            "method": "Depth-first enumeration of every START-to-END route",
            "inputs": f"{len(path_records)} distinct routes found (capped at {MAX_ENUMERATED_PATHS})",
        },
    ]

    return _report(
        report_type=REPORT_CRITICAL_PATH,
        title=f"Critical path and float explanation for {label}",
        headline={
            "label": "Zero-float bottleneck chain",
            "value": f"{len(critical_ids)} activities / {_days(critical_length)}",
            "tone": "critical" if critical_ids else "info",
        },
        summary=summary,
        narrative=narrative_sentences,
        cards=cards,
        metrics=metrics,
        evidence_trace=evidence_trace,
        confidence={
            "level": "HIGH",
            "basis": "Derived deterministically from the CPM forward/backward passes; no statistical assumptions are used.",
        },
    )


# ---------------------------------------------------------------------------
# (b) Probabilistic risk explanation with merge-path bias
# ---------------------------------------------------------------------------

def detect_merge_path_bias(
    nodes: Dict[str, cpm_engine.ActivityNode],
    merge_event_bias_threshold: float = DEFAULT_MERGE_EVENT_BIAS_THRESHOLD,
    min_combined_sd: float = MERGE_MIN_COMBINED_SD,
    max_gap_days: float = MERGE_MAX_GAP_DAYS,
) -> List[Dict[str, Any]]:
    """Detect merge events where parallel branches are separated by less than their noise.

    A merge event takes the project duration as the maximum of its incoming
    branch lengths. When two parallel branches reach the merge separated by
    less than their combined standard deviation, the nominally shorter branch
    governs completion a substantial share of the time even though CPM gives it
    only a token amount of float. The expected overshoot follows from
    E[max(X, Y)] - max(E) = sigma * phi(d) - d * (1 - Phi(d)).
    """
    detections: List[Dict[str, Any]] = []
    real = _real_nodes(nodes)

    for merge_id, merge_node in real.items():
        predecessor_ids = [s.get("pred_id") for s in merge_node.predecessor_specs
                           if s.get("pred_id") in real]
        if len(predecessor_ids) < 2:
            continue

        for index, left_id in enumerate(predecessor_ids):
            for right_id in predecessor_ids[index + 1:]:
                left = nodes[left_id]
                right = nodes[right_id]
                left_sigma = math.sqrt(max(0.0, left.variance or 0.0))
                right_sigma = math.sqrt(max(0.0, right.variance or 0.0))
                if left_sigma <= EPS and right_sigma <= EPS:
                    continue

                correlation = _branch_correlation(nodes, left_id, right_id)
                combined_variance = (
                    (left.variance or 0.0) + (right.variance or 0.0)
                    - 2.0 * correlation * left_sigma * right_sigma
                )
                combined_sigma = math.sqrt(max(0.0, combined_variance))
                if combined_sigma < min_combined_sd:
                    continue

                mean_gap = left.ef - right.ef
                later = left if left.ef >= right.ef else right
                earlier = right if later is left else left
                gap = abs(mean_gap)
                if gap > max_gap_days:
                    continue

                probability_earlier_governs = standard_normal_cdf(-gap / combined_sigma)
                bias_days = merge_event_bias_days(gap, combined_sigma)
                reference_length = max(later.ef, EPS)
                relative_bias = bias_days / reference_length
                shift_feasible = earlier.total_float >= gap - EPS

                if probability_earlier_governs >= merge_event_bias_threshold:
                    if probability_earlier_governs >= 0.35 and relative_bias >= 0.05:
                        severity = SEVERITY_CRITICAL
                    else:
                        severity = SEVERITY_WARNING
                else:
                    severity = SEVERITY_INFO

                detections.append({
                    "merge_activity_id": merge_id,
                    "merge_activity_name": merge_node.name,
                    "branch_a_id": later.id,
                    "branch_a_name": later.name,
                    "branch_a_finish": later.ef,
                    "branch_b_id": earlier.id,
                    "branch_b_name": earlier.name,
                    "branch_b_finish": earlier.ef,
                    "mean_gap_days": round(gap, 2),
                    "combined_sigma_days": round(combined_sigma, 2),
                    "branch_a_sigma_days": round(left_sigma, 2),
                    "branch_b_sigma_days": round(right_sigma, 2),
                    "correlation_assumption": correlation,
                    "merge_lag_days": round(later.ef - merge_node.es, 2),
                    "merge_event_bias_days": round(bias_days, 2),
                    "merge_event_bias": round(relative_bias, 4),
                    "probability_shorter_branch_governs": round(probability_earlier_governs, 4),
                    "float_shift_days": round(min(gap, earlier.total_float), 2),
                    "float_shift_feasible": bool(shift_feasible),
                    "float_shift_deficit_days": round(max(0.0, gap - earlier.total_float), 2),
                    "severity": severity,
                })

    detections.sort(key=lambda d: (d["severity"] != SEVERITY_CRITICAL,
                                   d["severity"] != SEVERITY_WARNING,
                                   -d["merge_event_bias"]))
    return detections


def _near_critical_path_cards(
    nodes: Dict[str, cpm_engine.ActivityNode],
    path_records: List[Dict[str, Any]],
    path_statistics: Dict[str, Any],
    near_critical_threshold: float,
) -> List[Dict[str, Any]]:
    """Explain alternative paths that simulation shows are co-critical.

    The frequency is taken from the seeded Monte Carlo ensemble rather than a
    closed-form approximation, because the frequency is exactly the quantity
    the planner needs and it is measured on the same sampling distribution the
    PERT model defines.
    """
    cards: List[Dict[str, Any]] = []
    path_means = path_statistics.get("path_means", {}) or {}
    path_sigmas = path_statistics.get("path_sigmas", {}) or {}
    frequencies = path_statistics.get("path_critical_frequencies", {}) or {}
    nominal_length = path_records[0]["length"]

    for record in path_records[1:]:
        key = " > ".join(record["activity_ids"])
        mean_length = path_means.get(key)
        sigma = path_sigmas.get(key)
        frequency = frequencies.get(key, 0.0)
        if frequency < near_critical_threshold:
            continue

        deterministic_gap = nominal_length - record["length"]
        narrative = (
            f"Monte Carlo sampling shows the route {_join_names(record['activity_names'], limit=4)} becomes the "
            f"critical path in {_percent(frequency)} of {path_statistics.get('num_simulations', 0)} simulated "
            f"projects, although deterministic CPM ranks it only {_days(deterministic_gap)} shorter than the "
            f"nominal critical path. Its simulated mean length is {_days(mean_length) if mean_length else 'n/a'} "
            f"with a standard deviation of {_days(sigma) if sigma else 'n/a'}, against a deterministic length of "
            f"{_days(record['length'])}: the mean already sits "
            f"{_days(float(mean_length) - record['length']) if mean_length else 'n/a'} above the deterministic figure, "
            f"and the spread pushes this route past the critical path in roughly {_percent(frequency)} of trials. "
            f"Any plan that treats it as spare capacity is planning for a failure mode."
        )

        evidence = _evidence([
            ("Simulated critical frequency", _percent(frequency)),
            ("Path mean length", _days(mean_length) if mean_length else "n/a"),
            ("Path standard deviation", _days(sigma) if sigma else "n/a"),
            ("Deterministic path length", _days(record["length"])),
            ("Deterministic path float", _days(record["path_float"])),
            ("Deterministic gap to critical", _days(deterministic_gap)),
            ("Simulations", str(path_statistics.get("num_simulations", 0))),
            ("Random seed", str(path_statistics.get("seed", ""))),
        ])

        actions = [_action(
            f"Treat {_join_names(record['activity_names'], limit=2)} as a co-critical branch for planning.",
            "Its simulated critical frequency exceeds the near-critical threshold, so resource and vendor bookings should not assume it is spare.",
            "HIGH" if frequency >= 0.5 else "MEDIUM",
            _percent(frequency),
        )]

        cards.append(_card(
            SEVERITY_CRITICAL if frequency >= 0.5 else SEVERITY_WARNING,
            "NEAR_CRITICAL_PATH",
            f"Near-critical path: {_join_names(record['activity_names'], limit=2)}",
            narrative,
            evidence=evidence,
            actions=actions,
            activity_ids=record["activity_ids"],
        ))
    return cards


def explain_probabilistic_risk(
    nodes: Dict[str, cpm_engine.ActivityNode],
    critical_path: Sequence[str],
    target_time: Optional[float] = None,
    probability: Optional[float] = None,
    expected_duration: Optional[float] = None,
    project_variance: Optional[float] = None,
    criticality_indices: Optional[Dict[str, float]] = None,
    merge_event_bias: Optional[List[Dict[str, Any]]] = None,
    path_statistics: Optional[Dict[str, Any]] = None,
    project_name: Optional[str] = None,
    mode: str = "CPM",
    near_critical_threshold: float = DEFAULT_NEAR_CRITICAL_THRESHOLD,
    deadline_buffer_percentile: int = 80,
) -> Dict[str, Any]:
    """Explain completion probability, merge-path bias and hidden criticality.

    Args:
        nodes: CPM network with PERT expected durations and variances.
        critical_path: Deterministic zero-float chain.
        target_time: Committed duration in days, or None when no deadline.
        probability: Analytical PERT probability of meeting ``target_time``.
        expected_duration: Expected project duration in days.
        project_variance: Sum of variances along the deterministic path.
        criticality_indices: ``{activity_id: percentage}`` from Monte Carlo.
        merge_event_bias: Pre-computed merge detections; computed when omitted.
        path_statistics: Output of :func:`simulate_path_statistics`.
    """
    real = _real_nodes(nodes)
    critical_ids = [cid for cid in critical_path if cid in real]
    critical_set = set(critical_ids)
    label = project_name or "this project"
    cards: List[Dict[str, Any]] = []
    evidence_trace: List[Dict[str, Any]] = []

    variance = project_variance if project_variance is not None else 0.0
    std_dev = math.sqrt(max(0.0, variance))
    expected = expected_duration if expected_duration is not None else 0.0
    z_score = None
    if target_time is not None and std_dev > EPS:
        z_score = (float(target_time) - expected) / std_dev
        if probability is None:
            probability = standard_normal_cdf(z_score)

    if probability is None and target_time is not None and std_dev <= EPS and expected > EPS:
        probability = 1.0 if float(target_time) >= expected - EPS else 0.0
        deterministic_verdict = probability >= 1.0
    else:
        deterministic_verdict = False

    if probability is None:
        headline = {"label": "Completion probability", "value": "not computable", "tone": "info"}
        cards.append(_card(
            SEVERITY_INFO,
            "PROBABILITY",
            "No probabilistic estimate available",
            ("A completion probability requires a target completion time and a non-zero project variance. "
             "Supply a target completion date or PERT estimates to unlock the risk diagnostics."),
            evidence=_evidence([
                ("Expected duration", _days(expected)),
                ("Project standard deviation", _days(std_dev)),
                ("Target time", _days(target_time) if target_time is not None else "not set"),
            ]),
        ))
    else:
        if probability >= 0.95:
            band, tone = "effectively certain", "success"
        elif probability >= 0.80:
            band, tone = "likely", "success"
        elif probability >= 0.50:
            band, tone = "marginal", "warning"
        else:
            band, tone = "at risk", "critical"

        deficit = max(0.0, expected - float(target_time)) if target_time is not None else 0.0
        slack = (float(target_time) - expected) if target_time is not None else 0.0
        slack_sigma_ratio = slack / std_dev if std_dev > EPS else None

        if deterministic_verdict:
            narrative = (
                f"Every activity on the critical path of {label} has identical optimistic, most-likely and "
                f"pessimistic estimates, so the project duration is not uncertain at all: it is exactly "
                f"{_days(expected)} days. The committed target of {_days(target_time)} days is therefore "
                f"{_days(slack)} days {'longer than, so the target will be met with certainty' if slack >= 0 else 'shorter than the duration, so the deadline will certainly be missed'}."
            )
            actions = []
            if slack < 0:
                actions.append(_action(
                    f"Move the committed date to {_days(expected)} or recover {_days(deficit)} from the critical path.",
                    "The estimates carry no uncertainty, so the deadline is missed with certainty rather than risk. This is a data problem, not a scheduling problem: either the estimates need real ranges or the date needs to move.",
                    "HIGH",
                    f"certain breach of {_days(deficit)}",
                ))
            else:
                actions.append(_action(
                    "Re-open the estimates to restore a usable risk model.",
                    "Identical three-point estimates make the PERT variance zero, which collapses the probability model and hides schedule risk entirely. Real planning needs a plausible spread on each estimate.",
                    "MEDIUM",
                    "variance 0.00",
                ))
            evidence_rows = [
                ("Expected duration (te)", _days(expected)),
                ("Project standard deviation", _days(std_dev)),
                ("Target time", _days(target_time)),
                ("Model", "deterministic, zero variance"),
                ("Headroom vs mean", f"{slack:+.2f} days"),
            ]
        else:
            z_phrase = (
                f", giving a Z-score of {z_score:+.2f} against the committed target of {_days(target_time)}"
                if z_score is not None and target_time is not None else ""
            )
            narrative = (
                f"The PERT model of {label} predicts an expected duration of {_days(expected)} with a standard "
                f"deviation of {_days(std_dev)}{z_phrase}. "
                f"The probability of finishing on time is {_percent(probability, 2)}, which is {band}."
            )
            if deficit > EPS:
                narrative += (
                    f" The commitment is already {_days(deficit)} shorter than the expected duration, so a breach is "
                    f"more likely than not and cannot be recovered by normal contingency."
                )

            actions = []
            if deficit > EPS:
                actions.append(_action(
                    f"Recover at least {_days(deficit)} from the critical path or renegotiate the date.",
                    "The target date sits below the expected duration, so every activity on the critical path must compress or the commitment must move.",
                    "HIGH",
                    f"Z = {z_score:+.2f}" if z_score is not None else None,
                ))
            elif slack_sigma_ratio is not None and slack_sigma_ratio < 0.5:
                actions.append(_action(
                    f"Add at least {_days(max(0.0, expected - (float(target_time) if target_time else 0.0) + 0.5 * std_dev))} of contingency.",
                    "The deadline sits less than half a standard deviation past the expected duration, so a routine overrun is enough to breach it.",
                    "HIGH",
                    f"{slack_sigma_ratio:+.2f} sigma of headroom",
                ))
            evidence_rows = [
                ("Expected duration (te)", _days(expected)),
                ("Project standard deviation", _days(std_dev)),
                ("Target time", _days(target_time) if target_time is not None else "not set"),
                ("Z-score", f"{z_score:+.3f}" if z_score is not None else "n/a"),
                ("P(T <= target) = Phi(Z)", _percent(probability, 2)),
                ("Headroom vs mean", f"{slack:+.2f} days"),
                ("Headroom in sigma", f"{slack_sigma_ratio:+.2f}" if slack_sigma_ratio is not None else "n/a"),
            ]

        cards.append(_card(
            (SEVERITY_CRITICAL if probability < 0.5 else (SEVERITY_WARNING if probability < 0.8 else SEVERITY_SUCCESS))
            if not deterministic_verdict or slack < 0 else SEVERITY_SUCCESS,
            "PROBABILITY" if not deterministic_verdict else "DETERMINISTIC_OUTCOME",
            (f"Completion probability {_percent(probability, 2)}" if not deterministic_verdict
             else ("Deadline will be met with certainty" if slack >= 0 else "Deadline will be missed with certainty")),
            narrative,
            evidence=_evidence(evidence_rows),
            actions=actions,
            activity_ids=critical_ids,
        ))

    evidence_trace.append({
        "step": "PERT expected duration",
        "method": "te = (a + 4m + b) / 6 ; var = ((b - a) / 6)^2",
        "inputs": f"Project variance = {variance:.4f}; standard deviation = {std_dev:.4f} days",
    })
    if z_score is not None:
        evidence_trace.append({
            "step": "Completion probability",
            "method": "Z = (target - te) / sqrt(var) ; P = Phi(Z)",
            "inputs": f"Z = {z_score:+.4f} -> P = {probability:.4f}",
        })
    elif deterministic_verdict:
        evidence_trace.append({
            "step": "Completion probability",
            "method": "Degenerate case: project variance is zero, so the outcome is decided by comparing the target with the expected duration",
            "inputs": f"target {_days(float(target_time))} vs expected {_days(expected)} -> P = {probability:.1f}",
        })

    bias_detections = merge_event_bias
    if bias_detections is None:
        bias_detections = detect_merge_path_bias(nodes)
        evidence_trace.append({
            "step": "Merge event bias detection",
            "method": "Bias = sigma*phi(d) - d*(1-Phi(d)), d = |EF_a - EF_b| / sigma ; P(shorter branch governs) = Phi(-d)",
            "inputs": f"{len(bias_detections)} merge events evaluated across {len(real)} activities",
        })

    for detection in bias_detections:
        if detection.get("severity") == SEVERITY_INFO and detection.get("merge_event_bias_days", 0.0) <= EPS:
            continue

        gap = detection["mean_gap_days"]
        actions = []
        if detection.get("float_shift_feasible"):
            actions.append(_action(
                f"Shift {_days(detection['float_shift_days'])} of float from '{detection['branch_b_name']}' to "
                f"'{detection['merge_activity_name']}' to balance the merge.",
                "Equalising the two branches removes the hidden merge bias and turns an unmonitored statistical risk into a known, deliberate buffer.",
                "HIGH",
                f"bias {_days(detection['merge_event_bias_days'])}",
            ))
        else:
            actions.append(_action(
                f"The {gap:.2f}-day gap between '{detection['branch_a_name']}' and '{detection['branch_b_name']}' "
                f"exceeds the available float, so add a merge milestone or compress the early branch.",
                f"'{detection['branch_b_name']}' only has {_days(detection['float_shift_days'])} of float to give, leaving a {_days(detection['float_shift_deficit_days'])} deficit that float-shifting alone cannot close.",
                "HIGH",
                f"deficit {_days(detection['float_shift_deficit_days'])}",
            ))

        actions.append(_action(
            f"Reduce the estimate spread on '{detection['branch_b_name']}' "
            f"(+-{_days(detection['branch_b_sigma_days'])}).",
            "Narrowing the duration distribution is usually cheaper than crashing and directly reduces the probability that this branch governs completion.",
            "MEDIUM",
            f"sigma {_days(detection['combined_sigma_days'])}",
        ))

        narrative = (
            f"'{detection['branch_a_name']}' reaches '{detection['merge_activity_name']}' at day "
            f"{detection['branch_a_finish']:.2f} and '{detection['branch_b_name']}' at day "
            f"{detection['branch_b_finish']:.2f}, a gap of only {_days(gap)} against a combined duration standard "
            f"deviation of {_days(detection['combined_sigma_days'])}. Because a merge event takes the maximum of its "
            f"incoming branches, '{detection['branch_b_name']}' - the branch CPM treats as safe - actually governs "
            f"completion in {_percent(detection['probability_shorter_branch_governs'], 2)} of trials, and the merge "
            f"overshoots the deterministic schedule by {_days(detection['merge_event_bias_days'])} on average."
        )
        if detection.get("correlation_assumption"):
            narrative += (" The two branches are treated as partially correlated (rho = "
                          f"{detection['correlation_assumption']}) because they share network logic.")

        cards.append(_card(
            detection.get("severity", SEVERITY_WARNING),
            "MERGE_PATH_BIAS",
            f"Merge-path bias at '{detection['merge_activity_name']}'",
            narrative,
            evidence=_evidence([
                ("Branch A finish (EF)", f"{detection['branch_a_finish']:.2f}"),
                ("Branch B finish (EF)", f"{detection['branch_b_finish']:.2f}"),
                ("Mean gap |d|", _days(gap)),
                ("Combined sigma", _days(detection["combined_sigma_days"])),
                ("Correlation assumption", f"rho = {detection['correlation_assumption']}"),
                ("P(shorter branch governs)", _percent(detection["probability_shorter_branch_governs"], 2)),
                ("Expected merge overshoot", _days(detection["merge_event_bias_days"])),
                ("Relative merge bias", _percent(detection["merge_event_bias"], 2)),
                ("Float available to shift", _days(detection["float_shift_days"])),
            ]),
            actions=actions,
            activity_ids=[detection["merge_activity_id"], detection["branch_b_id"]],
        ))

    if path_statistics:
        path_records = _path_records(nodes)
        cards.extend(_near_critical_path_cards(nodes, path_records, path_statistics, near_critical_threshold))
        evidence_trace.append({
            "step": "Near-critical path frequency",
            "method": "Fraction of simulated trials in which each distinct critical path governed completion",
            "inputs": f"{path_statistics.get('num_simulations', 0)} seeded simulations; "
                      f"{path_statistics.get('path_count', 0)} distinct critical paths observed",
        })

        deterministic_length = path_records[0]["length"] if path_records else 0.0
        simulated_mean = path_statistics.get("mean_duration")
        standard_error = float(path_statistics.get("mean_standard_error", 0.0) or 0.0)
        merge_events = sum(1 for node in real.values() if len(node.predecessors) > 1)
        if simulated_mean is not None and deterministic_length > EPS:
            empirical_bias = float(simulated_mean) - deterministic_length
            noise_floor = max(EPS, 2.0 * standard_error)
            if empirical_bias > noise_floor and merge_events > 0:
                share = empirical_bias / deterministic_length
                bias_severity = (
                    SEVERITY_CRITICAL if share >= 0.15 else
                    SEVERITY_WARNING if share >= 0.05 else SEVERITY_INFO
                )
                cards.insert(1, _card(
                    bias_severity,
                    "EMPIRICAL_MERGE_BIAS",
                    f"Deterministic schedule is optimistic by {_days(empirical_bias)}",
                    (f"The CPM critical path sums to {_days(deterministic_length)}, but the simulated mean "
                     f"completion time is {_days(simulated_mean)}. The {_days(empirical_bias)} gap "
                     f"({_percent(empirical_bias / deterministic_length, 1)} of the schedule) is the cumulative "
                     f"merge-event bias: a merge takes the maximum of its incoming branches, so every parallel "
                     f"merge in the network makes the real project longer than the sum of its critical activities. "
                     f"Any date committed from the CPM total alone is optimistic by this amount."),
                    evidence=_evidence([
                        ("Deterministic critical path", _days(deterministic_length)),
                        ("Simulated mean", _days(simulated_mean)),
                        ("Empirical merge bias", _days(empirical_bias)),
                        ("Bias as share of schedule", _percent(share, 1)),
                        ("Monte Carlo standard error", _days(standard_error)),
                        ("Merge events in network", str(merge_events)),
                        ("Simulated P95", _days((path_statistics.get("percentiles", {}) or {}).get("p95"))),
                        ("Simulations", str(path_statistics.get("num_simulations", 0))),
                    ]),
                    actions=[_action(
                        f"Add {_days(empirical_bias)} to the committed duration before negotiating a final date.",
                        "The deterministic critical path length systematically understates the project because of the maximum-of-branches operator at every merge.",
                        "HIGH",
                        _days(empirical_bias),
                    )],
                ))
            elif empirical_bias > EPS and merge_events == 0:
                cards.insert(1, _card(
                    SEVERITY_WARNING,
                    "ESTIMATOR_MISMATCH",
                    f"Simulated mean exceeds the schedule by {_days(empirical_bias)} with no merge to explain it",
                    (f"The CPM critical path sums to {_days(deterministic_length)} and the simulated mean is "
                     f"{_days(simulated_mean)}, a {_days(empirical_bias)} gap that is "
                     f"{empirical_bias / max(standard_error, EPS):.1f} times the Monte Carlo standard error of "
                     f"{_days(standard_error)}, so it is not sampling noise. The network contains no merge event, "
                     f"so the maximum-of-branches operator cannot produce it. Either the deterministic durations and "
                     f"the sampling distribution disagree, or the critical path switches between structurally "
                     f"equivalent routes inside the simulation. Do not commit a date from either figure until this "
                     f"is resolved."),
                    evidence=_evidence([
                        ("Deterministic critical path", _days(deterministic_length)),
                        ("Simulated mean", _days(simulated_mean)),
                        ("Observed gap", _days(empirical_bias)),
                        ("Monte Carlo standard error", _days(standard_error)),
                        ("Gap in standard errors", f"{empirical_bias / max(standard_error, EPS):.1f}"),
                        ("Merge events in network", "0"),
                        ("Simulations", str(path_statistics.get("num_simulations", 0))),
                    ]),
                ))
            elif empirical_bias > EPS:
                cards.append(_card(
                    SEVERITY_SUCCESS,
                    "NO_SIGNIFICANT_BIAS",
                    f"Simulated mean matches the schedule within {_days(abs(empirical_bias))}",
                    (f"The CPM critical path sums to {_days(deterministic_length)} and the simulated mean is "
                     f"{_days(simulated_mean)}. The {_days(empirical_bias)} difference is smaller than twice the "
                     f"Monte Carlo standard error of {_days(standard_error)}, so it is sampling noise rather than a "
                     f"real effect. The deterministic date is safe to commit on this network."),
                    evidence=_evidence([
                        ("Deterministic critical path", _days(deterministic_length)),
                        ("Simulated mean", _days(simulated_mean)),
                        ("Observed difference", _days(empirical_bias)),
                        ("Monte Carlo standard error", _days(standard_error)),
                        ("Merge events in network", str(merge_events)),
                        ("Simulations", str(path_statistics.get("num_simulations", 0))),
                    ]),
                ))

    indices = criticality_indices or {}
    hidden_drivers = [
        (activity_id, percentage)
        for activity_id, percentage in indices.items()
        if activity_id in real and activity_id not in critical_set
        and percentage / 100.0 >= DEFAULT_CRITICALITY_INDEX_THRESHOLD
    ]
    hidden_drivers.sort(key=lambda item: item[1], reverse=True)
    for activity_id, percentage in hidden_drivers[:4]:
        node = nodes[activity_id]
        cards.append(_card(
            SEVERITY_CRITICAL if percentage >= 50.0 else SEVERITY_WARNING,
            "HIDDEN_CRITICAL_ACTIVITY",
            f"Hidden driver: {node.name}",
            (f"'{node.name}' is not on the deterministic critical path, yet it appears on it in "
             f"{percentage:.1f}% of Monte Carlo trials. Its {_days(node.total_float)} of float is smaller than its "
             f"own {_days(node.duration)} duration variability, so the deterministic schedule systematically "
             f"understates its importance."),
            evidence=_evidence([
                ("Criticality index", f"{percentage:.2f}%"),
                ("Total float", _days(node.total_float)),
                ("Duration", _days(node.duration)),
                ("Standard deviation", _days(math.sqrt(max(0.0, node.variance or 0.0)))),
                ("Variance share", _percent(
                    (node.variance or 0.0) / variance if variance > EPS else None, 2)),
            ]),
            actions=[_action(
                f"Promote '{node.name}' to the monitored critical set.",
                f"Its {percentage:.1f}% simulated criticality means the plan, vendor bookings and crashing choices are all exposed to it.",
                "HIGH",
                f"{percentage:.1f}%",
            )],
            activity_ids=[activity_id],
        ))

    variance_contributors = sorted(
        [n for n in real.values() if (n.variance or 0.0) > EPS],
        key=lambda n: n.variance or 0.0,
        reverse=True,
    )
    if variance_contributors and variance > EPS:
        top = variance_contributors[:3]
        contribution = sum((n.variance or 0.0) for n in top) / variance
        cards.append(_card(
            SEVERITY_INFO,
            "VARIANCE_CONCENTRATION",
            "Where the schedule uncertainty lives",
            (f"{_percent(contribution, 1)} of the deterministic critical path variance is concentrated in "
             f"{_join_names([n.name for n in top], limit=3)}. Reducing the estimate spread on these activities "
             f"shrinks project standard deviation directly, whereas compressing durations on other activities does "
             f"not."),
            evidence=_evidence([
                ("Project variance", f"{variance:.4f}"),
                ("Project standard deviation", _days(std_dev)),
                ("Top contributors", _join_names([n.name for n in top], limit=3)),
                ("Concentration", _percent(contribution, 1)),
            ]),
            activity_ids=[n.id for n in top],
        ))

    if path_statistics:
        percentiles = path_statistics.get("percentiles", {}) or {}
        chosen = percentiles.get(f"p{deadline_buffer_percentile}")
        p95 = percentiles.get("p95")
        if chosen is not None:
            p80_action = _action(
                f"Set the internal commitment date at {_days(chosen)} (P{deadline_buffer_percentile}).",
                "Planning to the percentile rather than the mean converts stochastic risk into a single, datable milestone.",
                "MEDIUM",
                _days(chosen),
            )
            if p95 is not None:
                p80_action["rationale"] += (
                    f" The P95 date is {_days(p95)}, which is the point after which only 5% of simulated projects would still be running."
                )
            cards.append(_card(
                SEVERITY_INFO,
                "DEADLINE_BUFFER",
                f"Probabilistic deadline: P{deadline_buffer_percentile} at {_days(chosen)}",
                (f"Across simulated projects the mean duration is "
                 f"{_days(path_statistics.get('mean_duration'))}, the P50 is {_days(percentiles.get('p50'))} and the "
                 f"P95 is {_days(p95)}. Committing to the mean leaves an unquantified chance of missing the date; "
                 f"committing to the P{deadline_buffer_percentile} absorbs the routine variability."),
                evidence=_evidence([
                    ("Mean", _days(path_statistics.get("mean_duration"))),
                    ("P50", _days(percentiles.get("p50"))),
                    (f"P{deadline_buffer_percentile}", _days(chosen)),
                    ("P90", _days(percentiles.get("p90"))),
                    ("P95", _days(p95)),
                    ("Simulations", str(path_statistics.get("num_simulations", 0))),
                    ("Random seed", str(path_statistics.get("seed", ""))),
                ]),
                actions=[p80_action],
            ))
        evidence_trace.append({
            "step": "Monte Carlo path simulation",
            "method": "Seeded triangular sampling of the PERT three-point estimates with full CPM re-solve per trial",
            "inputs": f"{path_statistics.get('num_simulations', 0)} trials, seed {path_statistics.get('seed')}",
        })

    if not cards:
        cards.append(_card(
            SEVERITY_SUCCESS,
            "NO_RISK_SIGNALS",
            "No material risk signals",
            "The network shows no zero-float bottleneck concentration, no statistically fragile merge events and no hidden criticality indices.",
        ))

    flagged = [d for d in (bias_detections or []) if d.get("severity") == SEVERITY_CRITICAL]
    bias_total = sum(d["merge_event_bias_days"] for d in (bias_detections or []))
    if probability is not None:
        headline = {
            "label": "On-time completion probability",
            "value": _percent(probability, 2),
            "tone": "critical" if probability < 0.5 else ("warning" if probability < 0.8 else "success"),
        }
    else:
        headline = {"label": "On-time completion probability", "value": "not computable", "tone": "info"}

    if not real:
        summary = (
            f"{label} has no activities, so there is no schedule to take a probability against. Expected duration, "
            f"variance and merge effects are all zero by construction rather than by measurement. Add activities with "
            f"three-point estimates to activate the risk diagnostics."
        )
        narrative_sentences = [
            f"{label} contains 0 activities.",
            "No probability, variance or merge-bias figure can be derived from an empty network.",
            "Add activities with optimistic, most-likely and pessimistic estimates to unlock risk diagnostics.",
        ]
    else:
        probability_phrase = (
            f"carries a completion probability of {_percent(probability, 2)} against its target of {_days(target_time)}"
            if probability is not None and target_time is not None else
            f"carries no completion probability, because {'no target completion date is set' if target_time is None else 'the project variance is zero'}"
        )
        summary = (
            f"{label} {probability_phrase}. "
            f"{len(flagged)} merge events are statistically fragile and together they inflate the expected duration by "
            f"{_days(bias_total)} through the PERT merge-bias effect. "
            f"{len(hidden_drivers)} activities are hidden critical drivers that the deterministic schedule does not reveal."
        )

        narrative_sentences = [
            f"Expected duration {_days(expected)} with standard deviation {_days(std_dev)}.",
            f"Merge events evaluated: {len(bias_detections or [])}; statistically fragile: {len(flagged)}.",
            f"Aggregate expected merge overshoot: {_days(bias_total)}.",
            f"Hidden critical activities (criticality index above {_percent(DEFAULT_CRITICALITY_INDEX_THRESHOLD, 0)} off-path): {len(hidden_drivers)}.",
        ]

    metrics = {
        "expected_duration_days": round(expected, 2),
        "project_variance": round(variance, 4),
        "project_standard_deviation_days": round(std_dev, 4),
        "target_time_days": round(float(target_time), 2) if target_time is not None else None,
        "z_score": round(z_score, 4) if z_score is not None else None,
        "completion_probability": round(probability, 4) if probability is not None else None,
        "merge_event_count": len(bias_detections or []),
        "merge_event_bias_days_total": round(bias_total, 3),
        "hidden_critical_activity_count": len(hidden_drivers),
        "mode": mode,
    }

    confidence_level = "HIGH" if probability is not None and path_statistics else (
        "MEDIUM" if probability is not None else "LOW"
    )
    confidence_basis = (
        "Analytical PERT Z-score combined with a seeded, reproducible Monte Carlo ensemble."
        if path_statistics else
        ("Analytical PERT Z-score; the normal approximation assumes the critical path is fixed."
         if probability is not None else
         "Insufficient information: no target completion time or no PERT variance available.")
    )

    return _report(
        report_type=REPORT_RISK,
        title=f"Probabilistic risk explanation for {label}",
        headline=headline,
        summary=summary,
        narrative=narrative_sentences,
        cards=cards,
        metrics=metrics,
        evidence_trace=evidence_trace,
        confidence={"level": confidence_level, "basis": confidence_basis},
    )


# ---------------------------------------------------------------------------
# (c) Counterfactual schedule crashing explanation
# ---------------------------------------------------------------------------

def _crashable_pool(activities: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    pool: Dict[str, Dict[str, Any]] = {}
    for activity in activities:
        activity_id = str(activity.get("id"))
        normal_duration = _effective_duration(activity)
        crash_value = activity.get("crash_duration")
        crash_duration = normal_duration if crash_value is None else min(float(crash_value), normal_duration)
        normal_cost = float(activity.get("normal_cost") or 0.0)
        crash_cost = normal_cost if activity.get("crash_cost") is None else float(activity["crash_cost"])
        max_crashable = max(0.0, normal_duration - crash_duration)
        cost_per_day = (crash_cost - normal_cost) / max_crashable if max_crashable > EPS else float("inf")
        pool[activity_id] = {
            "id": activity_id,
            "name": activity.get("name", activity_id),
            "normal_duration": normal_duration,
            "crash_duration": crash_duration,
            "max_crashable": max_crashable,
            "normal_cost": normal_cost,
            "crash_cost": crash_cost,
            "cost_per_day": max(0.0, cost_per_day),
            "category": activity.get("category"),
            "vendor_name": activity.get("vendor_name"),
        }
    return pool


def _effective_duration(activity: Dict[str, Any]) -> float:
    duration = float(activity.get("duration") or 0.0)
    if duration > EPS:
        return duration
    opt = activity.get("optimistic_time")
    likely = activity.get("most_likely_time")
    pess = activity.get("pessimistic_time")
    if opt is None or likely is None or pess is None:
        return duration
    return (float(opt) + 4.0 * float(likely) + float(pess)) / 6.0


def _normalise_activities(activities: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Resolve each activity's duration, falling back to the PERT expected time.

    PERT rows persist ``duration = 0`` because their real length lives in the
    three-point estimates, so any internal CPM pass must resolve it first or the
    network collapses to a zero-length graph.
    """
    normalised: List[Dict[str, Any]] = []
    for activity in activities:
        clone = dict(activity)
        clone["duration"] = _effective_duration(activity)
        normalised.append(clone)
    return normalised


def _lock_activities(activities: Sequence[Dict[str, Any]], locked: Sequence[str]) -> List[Dict[str, Any]]:
    locked_set = {str(a) for a in locked}
    adjusted: List[Dict[str, Any]] = []
    for activity in activities:
        clone = dict(activity)
        if str(activity.get("id")) in locked_set:
            clone["crash_duration"] = _effective_duration(activity)
        adjusted.append(clone)
    return adjusted


def _structural_rejection_cards(
    on_path: List[Dict[str, Any]],
    off_path_cheaper: List[Dict[str, Any]],
    result: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Explain cheaper crash candidates that the optimiser could not use.

    These activities are genuine candidates on price but sit off the baseline
    critical path, so spending money on them does not move the project date.
    One of them may still be compressed later in the sequence once the cheaper
    critical activities exhaust their crash limits, which is worth stating so the
    report does not read as a contradiction.
    """
    if not on_path or not off_path_cheaper:
        return []

    cards: List[Dict[str, Any]] = []
    chosen_slope = min(entry["cost_per_day"] for entry in on_path)
    compressed_ids = {str(item.get("activity_id")) for item in result.get("crashed_activities", [])}
    for entry in off_path_cheaper[:3]:
        saving = chosen_slope - entry["cost_per_day"]
        later_eligible = entry["id"] in compressed_ids
        if later_eligible:
            consequence = (
                " The plan below does compress it later in the sequence, because the cheaper critical activities "
                "exhaust their crash limits first and hand the critical path over to it. Its low cost slope is what "
                "keeps the average rate of the whole plan down instead of forcing a steeper alternative."
            )
        else:
            consequence = (
                " It becomes useful only once a critical activity consumes all of its own float, at which point it "
                "is the cheapest lever available."
            )
        cards.append(_card(
            SEVERITY_INFO,
            "STRUCTURAL_REJECTION",
            f"Cheaper but off the critical path: {entry['name']}",
            (f"'{entry['name']}' can be compressed for {_money(entry['cost_per_day'])} per day, which is "
             f"{_money(saving)} per day cheaper than the {_money(chosen_slope)} per day available on the baseline "
             f"critical path. It is excluded at that point only because it does not sit on the critical path: "
             f"compressing a non-critical activity by definition does not shorten the project."
             f"{consequence}"),
            evidence=_evidence([
                ("Cost per day", _money(entry["cost_per_day"])),
                ("Baseline critical path rate", _money(chosen_slope)),
                ("Discount per day", _money(saving)),
                ("Compressible by", _days(entry["max_crashable"])),
                ("On baseline critical path", "no"),
                ("Compressed later in the plan", "yes" if later_eligible else "no"),
            ]),
            activity_ids=[entry["id"]],
        ))
    return cards


def explain_schedule_crashing(
    activities: Sequence[Dict[str, Any]],
    baseline_duration: float,
    target_duration: Optional[float] = None,
    max_budget: Optional[float] = None,
    crash_result: Optional[Dict[str, Any]] = None,
    project_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Explain why the crashing heuristic selected specific activities.

    The crashing engine follows the classic linear time-cost trade-off rule:
    repeatedly compress the cheapest crashable activity *on the current
    critical path*. This function reproduces the candidate set, evaluates
    counterfactual plans in which the chosen activities are locked out, and
    narrates the trade-off, including structural rejections of cheaper
    off-path activities.
    """
    label = project_name or "this project"
    pool = _crashable_pool(activities)
    normalised = _normalise_activities(activities)
    nodes, critical_path, measured_duration = cpm_engine.calculate_cpm(normalised)
    baseline_duration = baseline_duration or measured_duration
    critical_set = set(critical_path)

    cards: List[Dict[str, Any]] = []
    on_path = [
        pool[a] for a in critical_path
        if a in pool and pool[a]["max_crashable"] > EPS and pool[a]["cost_per_day"] < float("inf")
    ]
    off_path_cheaper = sorted(
        [
            entry for activity_id, entry in pool.items()
            if activity_id not in critical_set
            and entry["max_crashable"] > EPS
            and entry["cost_per_day"] < float("inf")
            and (on_path and entry["cost_per_day"] < min(e["cost_per_day"] for e in on_path))
        ],
        key=lambda e: e["cost_per_day"],
    )

    resolved_target = target_duration
    if resolved_target is None and max_budget is None and on_path:
        exhausted = cpm_engine.crash_project_network(normalised, target_duration=0.0, max_budget=None)
        resolved_target = float(exhausted.get("crashed_duration", baseline_duration) or 0.0)
    if resolved_target is None:
        resolved_target = baseline_duration

    # `resolved_target` is a display fallback for the narrative and is NOT the
    # optimisation constraint. The upstream engine stops the moment
    # current_duration <= target_duration, so substituting a fallback here would
    # turn a budget-only request into a silent no-op. Pass the caller's actual
    # target: it self-no-ops when already satisfied, and None lets the budget
    # drive the compression when no target was requested.
    result = crash_result or cpm_engine.crash_project_network(
        normalised,
        target_duration=target_duration,
        max_budget=max_budget,
    )

    cards.extend(_structural_rejection_cards(on_path, off_path_cheaper, result))

    crashed = list(result.get("crashed_activities", []))
    days_saved = float(result.get("total_days_saved", 0.0) or 0.0)
    additional_cost = float(result.get("additional_crash_cost", 0.0) or 0.0)
    achieved_rate = additional_cost / days_saved if days_saved > EPS else 0.0

    empty_network = not normalised
    if days_saved <= EPS and not empty_network:
        cards.insert(0, _card(
            SEVERITY_WARNING,
            "NO_CRASH_OPTIONS",
            "No compression plan is feasible",
            (f"None of the {len(on_path)} crashable activities on the critical path could be reduced within the "
             f"constraints supplied. Either the target duration is already satisfied, the budget is exhausted, or the "
             f"critical activities have no crash_duration or crash_cost defined, so EventPath cannot trade time for "
             f"money on this network."),
            evidence=_evidence([
                ("Baseline duration", _days(baseline_duration)),
                ("Requested target", _days(target_duration) if target_duration is not None else "not set"),
                ("Budget cap", _money(max_budget) if max_budget is not None else "not set"),
                ("Crashable critical activities", str(len(on_path))),
            ]),
            actions=[_action(
                "Populate crash_duration and crash_cost on the critical activities.",
                "Without a crash limit and a crash cost the engine cannot compute a cost per day and must stop at the baseline duration.",
                "HIGH",
                f"{len(on_path)} crashable",
            )],
        ))
    else:
        crashed_by_id = {str(item.get("activity_id")): item for item in crashed}
        ordered = sorted(
            [(item, pool.get(str(item.get("activity_id")), {})) for item in crashed],
            key=lambda pair: float(pair[0].get("cost_per_day", 0.0) or 0.0),
        )

        for index, (item, entry) in enumerate(ordered):
            activity_id = str(item.get("activity_id"))
            days = float(item.get("days_crashed", 0.0) or 0.0)
            rate = float(item.get("cost_per_day", 0.0) or 0.0)
            spent = float(item.get("total_crash_cost", 0.0) or 0.0)
            still_critical = activity_id in set(result.get("final_critical_path", []) or [])

            alternatives = sorted(
                [e for a, e in pool.items()
                 if a != activity_id and a in critical_set
                 and e["max_crashable"] > EPS and e["cost_per_day"] < float("inf")],
                key=lambda e: e["cost_per_day"],
            )
            runner_up = alternatives[0] if alternatives else None

            if runner_up is None:
                runner_up_clause = (
                    " It is the only crashable activity on the critical path, so the rule has no alternative to "
                    "consider and must buy its days here or not at all."
                )
            elif rate <= runner_up["cost_per_day"] + EPS:
                runner_up_clause = (
                    f" At {_money(rate)} per day it is the cheapest crashable activity on the critical path - "
                    f"'{runner_up['name']}' costs {_money(runner_up['cost_per_day'])} per day - so the "
                    f"time-cost trade-off rule selects it first."
                )
            else:
                exhausted = crashed_by_id.get(str(runner_up["id"]))
                exhausted_days = float(exhausted.get("days_crashed", 0.0) or 0.0) if exhausted else 0.0
                if exhausted_days >= runner_up["max_crashable"] - EPS:
                    runner_up_clause = (
                        f" It is {_money(rate - runner_up['cost_per_day'])} per day more expensive than "
                        f"'{runner_up['name']}', and was selected only after that activity's "
                        f"{_days(runner_up['max_crashable'])} of crashable capacity was fully consumed at "
                        f"{_money(runner_up['cost_per_day'])} per day. This is the classic step-function behaviour "
                        f"of linear crashing: buy the cheap capacity first, then pay the next slope up."
                    )
                else:
                    runner_up_clause = (
                        f" It is {_money(rate - runner_up['cost_per_day'])} per day more expensive than "
                        f"'{runner_up['name']}', which still has unused crashable capacity. The saving therefore "
                        f"comes from the interaction with the compressed network rather than from this slope alone."
                    )

            actions = [_action(
                f"Compress '{item.get('activity_name')}' by {_days(days)} at {_money(rate)} per day.",
                "It is the cheapest crashable activity on the current critical path, so each day bought here translates directly into project duration at the lowest cost.",
                "HIGH",
                _money(spent),
            )]

            if index < MAX_CRASH_COUNTERFACTUALS:
                counterfactual_note = _crash_counterfactual(
                    normalised, activity_id, resolved_target, max_budget, result
                )
                if counterfactual_note is not None:
                    actions.append(_action(
                        counterfactual_note["action"],
                        counterfactual_note["rationale"],
                        "MEDIUM",
                        counterfactual_note["metric"],
                    ))

            shift_clause = (
                " It remains on the compressed critical path, so the saving flows straight to the project date."
                if still_critical else
                " It left the critical path after compression, meaning a second path has taken over as the driver; "
                "the saving is real but further compression here no longer shortens the project."
            )

            cards.append(_card(
                SEVERITY_INFO,
                "CRASH_SELECTION" if index == 0 else "CRASH_SUPPLEMENT",
                f"Compressed: {item.get('activity_name')}",
                (f"'{item.get('activity_name')}' was reduced from {_days(item.get('original_duration', 0.0))} to "
                 f"{_days(item.get('crashed_duration', 0.0))} for {_money(spent)}, buying {_days(days)} at "
                 f"{_money(rate)} per day. The selection rule is the classic linear time-cost trade-off: compress the "
                 f"cheapest crashable activity on the current critical path, because only critical activities move "
                 f"the project date.{runner_up_clause}{shift_clause}"),
                evidence=_evidence([
                    ("Original duration", _days(item.get("original_duration", 0.0))),
                    ("Crashed duration", _days(item.get("crashed_duration", 0.0))),
                    ("Days recovered", _days(days)),
                    ("Cost per day", _money(rate)),
                    ("Total crash cost", _money(spent)),
                    ("Still critical", "yes" if still_critical else "no"),
                    ("Critical alternatives", ", ".join(
                        f"{e['name']} @ {_money(e['cost_per_day'])}/day" for e in alternatives[:3]) or "none"),
                ]),
                actions=actions,
                activity_ids=[activity_id],
            ))

    if days_saved > EPS and additional_cost > EPS:
        steepest = max(
            (float(i.get("cost_per_day", 0.0) or 0.0) for i in crashed), default=0.0
        )
        budget_action = None
        if max_budget is not None and additional_cost >= max_budget - EPS:
            budget_action = _action(
                f"Budget exhausted at {_money(additional_cost)}; raise the cap or accept the longer date.",
                "The optimiser stopped because the cost cap bound, not because the network ran out of crashable time. "
                "The remaining days are purchasable at the slopes listed in the evidence.",
                "MEDIUM",
                f"{_percent(additional_cost / max_budget if max_budget else None, 0)} of cap",
            )
        cards.append(_card(
            SEVERITY_WARNING if (max_budget is not None and additional_cost >= max_budget - EPS) else SEVERITY_INFO,
            "COST_EFFICIENCY",
            f"Achieved cost efficiency {_money(achieved_rate)} per day",
            (f"The plan recovered {_days(days_saved)} of project duration for {_money(additional_cost)}, an average "
             f"of {_money(achieved_rate)} per day against a steepest single day of {_money(steepest)}. Because the "
             f"cost-per-day slope is a step function, the average hides the marginal price of the final day: the last "
             f"day bought costs up to {_money(steepest)}, so check the steepest day rather than the average when "
             f"justifying the spend."),
            evidence=_evidence([
                ("Days recovered", _days(days_saved)),
                ("Additional cost", _money(additional_cost)),
                ("Average cost per day", _money(achieved_rate)),
                ("Steepest day cost", _money(steepest)),
                ("New duration", _days(result.get("crashed_duration", baseline_duration))),
                ("Budget cap", _money(max_budget) if max_budget is not None else "not set"),
                ("Budget utilisation", _percent(
                    additional_cost / max_budget if max_budget not in (None, 0) else None, 1)),
            ]),
            actions=[budget_action] if budget_action else [],
        ))

    if days_saved > EPS and float(result.get("crashed_duration", 0.0) or 0.0) > float(resolved_target) + EPS:
        cards.append(_card(
            SEVERITY_WARNING,
            "TARGET_NOT_REACHED",
            "Requested compression could not be fully delivered",
            (f"The target of {_days(resolved_target)} was not reached: the plan stops at "
             f"{_days(result.get('crashed_duration'))} because every remaining critical activity has no crash limit "
             f"or no cost slope. Delivering the remaining "
             f"{_days(float(result.get('crashed_duration', 0.0)) - float(resolved_target))} requires either new "
             f"crash_cost data or a structural change such as rescoping, fast-tracking or replacing a critical "
             f"vendor."),
            evidence=_evidence([
                ("Requested target", _days(resolved_target)),
                ("Achieved", _days(result.get("crashed_duration"))),
                ("Shortfall", _days(float(result.get("crashed_duration", 0.0)) - float(resolved_target))),
            ]),
            actions=[_action(
                "Add crash_duration and crash_cost to the remaining critical activities.",
                "Without cost slopes the linear trade-off rule has no candidate left to select.",
                "HIGH",
                f"shortfall {_days(float(result.get('crashed_duration', 0.0)) - float(resolved_target))}",
            )],
        ))

    if empty_network:
        summary = (
            f"{label} has no activities, so there is nothing to compress. No baseline duration, no critical path and "
            f"no cost slope exist, and the crashing optimiser has nothing to select. Add activities with "
            f"crash_duration and crash_cost values to make compression trade-offs computable."
        )
        narrative_sentences = [
            f"{label} contains 0 crashable activities.",
            "Baseline and crashed durations are both 0.00 days because the network is empty.",
            "No cost efficiency can be computed without a critical path to shorten.",
        ]
    else:
        summary = (
            f"Compressing {label} from {_days(baseline_duration)} to {_days(result.get('crashed_duration'))} costs "
            f"{_money(additional_cost)}, buying {_days(days_saved)} at an average of {_money(achieved_rate)} per day. "
            f"The engine spent that money on the lowest cost-per-day activities sitting on the critical path; "
            f"{len(off_path_cheaper)} cheaper off-path "
            f"{'activity was' if len(off_path_cheaper) == 1 else 'activities were'} structurally excluded because "
            f"compressing {'it' if len(off_path_cheaper) == 1 else 'them'} cannot move the project date."
        )

        narrative_sentences = [
            f"Baseline duration {_days(baseline_duration)}; compressed to {_days(result.get('crashed_duration'))}.",
            f"Achieved cost per day {_money(achieved_rate)} across {_days(days_saved)} recovered.",
            f"Activities compressed: {len(crashed)} ({', '.join(str(i.get('activity_name')) for i in crashed) or 'none'}).",
            f"Cheaper off-path activities structurally excluded: {len(off_path_cheaper)}.",
        ]

    metrics = {
        "baseline_duration_days": round(baseline_duration, 2),
        "crashed_duration_days": round(float(result.get("crashed_duration", baseline_duration) or 0.0), 2),
        "days_saved": round(days_saved, 2),
        "additional_crash_cost": round(additional_cost, 2),
        "average_cost_per_day": round(achieved_rate, 2),
        "baseline_cost": round(float(result.get("baseline_cost", 0.0) or 0.0), 2),
        "final_total_cost": round(float(result.get("final_total_cost", 0.0) or 0.0), 2),
        "crashed_activity_count": len(crashed),
        "target_duration_days": round(resolved_target, 2),
        "max_budget": round(float(max_budget), 2) if max_budget is not None else None,
        "critical_path_activity_count": len(critical_set),
    }

    evidence_trace = [
        {
            "step": "Baseline CPM",
            "method": "Forward/backward pass on the unmodified durations",
            "inputs": f"Duration {_days(baseline_duration)}; critical path of {len(critical_set)} activities",
        },
        {
            "step": "Cost slope computation",
            "method": "cost per day = (crash_cost - normal_cost) / (normal_duration - crash_duration)",
            "inputs": f"{len(on_path)} crashable critical activities; {len(off_path_cheaper)} cheaper off-path activities rejected",
        },
        {
            "step": "Iterative critical-path crashing",
            "method": "Repeat: recompute CPM, pick min(cost per day) among crashable critical activities, compress 1 day",
            "inputs": f"Target {_days(resolved_target)}; budget {_money(max_budget) if max_budget is not None else 'unbounded'}",
        },
    ]
    if days_saved > EPS:
        evidence_trace.append({
            "step": "Counterfactual lock-out",
            "method": "Re-run the crashing engine with the selected activity made incompressible, then compare totals",
            "inputs": f"{min(MAX_CRASH_COUNTERFACTUALS, len(crashed))} counterfactual plans evaluated",
        })

    confidence = {
        "level": "HIGH" if days_saved > EPS else "MEDIUM",
        "basis": (
            "The optimality claim is bounded by the linear time-cost assumption and by the completeness of the "
            "crash_cost and crash_duration data on the project."
        ),
    }

    return _report(
        report_type=REPORT_CRASHING,
        title=f"Counterfactual crashing trade-off for {label}",
        headline={
            "label": "Cost per day recovered",
            "value": _money(achieved_rate) if days_saved > EPS else "no feasible plan",
            "tone": "info" if days_saved > EPS else "warning",
        },
        summary=summary,
        narrative=narrative_sentences,
        cards=cards,
        metrics=metrics,
        evidence_trace=evidence_trace,
        confidence=confidence,
    )


def _crash_counterfactual(
    activities: Sequence[Dict[str, Any]],
    locked_activity_id: str,
    target_duration: float,
    max_budget: Optional[float],
    selected_result: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Re-run crashing with one activity locked out to justify the choice."""
    try:
        alternative = cpm_engine.crash_project_network(
            _lock_activities(activities, [locked_activity_id]),
            target_duration=target_duration if target_duration > 0 else None,
            max_budget=max_budget,
        )
    except Exception:
        return None

    alt_days = float(alternative.get("total_days_saved", 0.0) or 0.0)
    alt_cost = float(alternative.get("additional_crash_cost", 0.0) or 0.0)
    sel_days = float(selected_result.get("total_days_saved", 0.0) or 0.0)
    sel_cost = float(selected_result.get("additional_crash_cost", 0.0) or 0.0)
    locked_name = _crashable_pool(activities).get(locked_activity_id, {}).get(
        "name", locked_activity_id
    )

    if alt_days < sel_days - EPS:
        return {
            "action": f"Essential: excluding '{locked_name}' forfeits {_days(sel_days - alt_days)} of compression.",
            "rationale": (
                f"Re-running the optimiser with this activity made incompressible recovers only {_days(alt_days)} "
                f"against {_days(sel_days)} with it enabled, so it carries compression that nothing else on the "
                f"network can supply. It is not interchangeable, and the plan has no substitute for it."
            ),
            "metric": f"-{_days(sel_days - alt_days)} without it",
        }

    if alt_cost > sel_cost + EPS:
        return {
            "action": f"Counterfactual: excluding '{locked_name}' costs {_money(alt_cost)} instead of "
                      f"{_money(sel_cost)} for the same target.",
            "rationale": (
                f"Re-running the optimiser with this activity made incompressible still recovers {_days(alt_days)} "
                f"for {_money(alt_cost)}, against {_money(sel_cost)} with it enabled. The selection is therefore "
                f"cost-optimal within the linear trade-off model, not an artefact of tie-breaking."
            ),
            "metric": f"+{_money(alt_cost - sel_cost)}",
        }

    if alt_cost < sel_cost - EPS or alt_days > sel_days + EPS:
        return {
            "action": f"Caution: a plan without '{locked_name}' would be cheaper - {_money(alt_cost)} for "
                      f"{_days(alt_days)} against {_money(sel_cost)} for {_days(sel_days)}.",
            "rationale": (
                f"Locking this activity out and re-solving the network produces a strictly better outcome, which "
                f"means the greedy cheapest-slope rule is not globally optimal here. This happens when "
                f"compressing a critical activity pushes another path into the critical set at a lower marginal "
                f"rate. Treat the published plan as a strong heuristic, not a proven optimum, and check the "
                f"alternative before committing budget."
            ),
            "metric": f"{_money(sel_cost - alt_cost)} cheaper",
        }

    return {
        "action": f"Counterfactual: excluding '{locked_name}' yields an equivalent plan at the same cost.",
        "rationale": (
            f"With this activity locked out the engine still recovers {_days(alt_days)} for {_money(alt_cost)}, so "
            f"several activities are interchangeable at the margin. That redundancy is a negotiating asset: any one "
            f"vendor can be replaced without losing schedule."
        ),
        "metric": f"{_money(alt_cost)}",
    }


# ---------------------------------------------------------------------------
# (d) Vendor conflict explanation with float-shifting proposals
# ---------------------------------------------------------------------------

def explain_vendor_conflicts(
    conflicts: Sequence[Dict[str, Any]],
    project_start_date: Any = None,
    project_name: Optional[str] = None,
    nodes: Optional[Dict[str, cpm_engine.ActivityNode]] = None,
    float_tolerance_days: float = 0.5,
) -> Dict[str, Any]:
    """Translate vendor calendar collisions into actionable float-shift advice.

    Args:
        conflicts: Rows produced by ``project_service.check_vendor_availability``.
        project_start_date: Calendar anchor used to date the float shifts.
        project_name: Project label used in the narrative.
        nodes: Optional CPM network used to recover precise float figures.
    """
    label = project_name or "this project"
    cards: List[Dict[str, Any]] = []
    nodes = nodes or {}
    anchor = _iso(project_start_date)
    used = {"float_shift": 0, "extend_window": 0, "split_booking": 0, "escalate": 0}

    def float_of(conflict: Dict[str, Any]) -> float:
        activity_id = str(conflict.get("activity_id"))
        if activity_id in nodes:
            return float(nodes[activity_id].total_float)
        return float(conflict.get("total_float", 0.0) or 0.0)

    def free_float_of(conflict: Dict[str, Any]) -> float:
        activity_id = str(conflict.get("activity_id"))
        if activity_id in nodes:
            return float(nodes[activity_id].free_float)
        return 0.0

    for conflict in conflicts:
        conflict_type = str(conflict.get("conflict_type", ""))
        activity_id = str(conflict.get("activity_id"))
        activity_name = conflict.get("activity_name", activity_id)
        vendor = conflict.get("vendor_name") or "an unassigned vendor"
        total_float = float_of(conflict)
        free_float = free_float_of(conflict)
        actions: List[Dict[str, str]] = []

        if conflict_type == "VENDOR_OVERBOOKING":
            other_id = str(conflict.get("conflicting_activity_id"))
            other_name = conflict.get("conflicting_activity_name", other_id)
            start = conflict.get("scheduled_start")
            finish = conflict.get("scheduled_finish")
            overlap_days = _overlap_days(start, finish, other_id, conflict, nodes, anchor)

            shift_forward = min(overlap_days, total_float) if total_float > EPS else 0.0
            shift_feasible = total_float >= overlap_days - float_tolerance_days

            if shift_feasible:
                new_start = _add_days(start, overlap_days)
                actions.append(_action(
                    f"Delay '{activity_name}' by {_days(shift_forward)} to start on "
                    f"{_iso(new_start)}, after '{other_name}' releases {vendor}.",
                    f"'{activity_name}' holds {_days(total_float)} of float, which covers the {_days(overlap_days)} "
                    f"overlap, so the reshuffle costs zero project days.",
                    "HIGH",
                    f"{_days(shift_forward)} of {_days(total_float)} float",
                ))
                used["float_shift"] += 1
                severity = SEVERITY_WARNING
                narrative = (
                    f"{vendor} is double-booked: '{activity_name}' ({_iso(start)} to {_iso(finish)}) overlaps "
                    f"'{other_name}' for {_days(overlap_days)}. '{activity_name}' holds {_days(total_float)} of float, "
                    f"so its {_days(overlap_days)}-day overlap can be absorbed by shifting its start from "
                    f"{_iso(start)} to {_iso(new_start)} without moving the project finish date."
                )
                evidence = _evidence([
                    ("Vendor", str(vendor)),
                    ("Overlap", _days(overlap_days)),
                    ("Total float", _days(total_float)),
                    ("Free float", _days(free_float)),
                    ("Proposed new start", _iso(new_start)),
                    ("Project impact", "0 days"),
                ])
            else:
                deficit = max(0.0, overlap_days - total_float)
                actions.append(_action(
                    f"The {_days(overlap_days)} overlap exceeds the {_days(total_float)} of float on "
                    f"'{activity_name}' by {_days(deficit)}; split the booking or compress the activity.",
                    "Pure float-shifting cannot close the gap, so the constraint has to be handled commercially or structurally rather than by rescheduling.",
                    "HIGH",
                    f"deficit {_days(deficit)}",
                ))
                actions.append(_action(
                    f"Negotiate a two-team or split-day engagement with {vendor}.",
                    f"Two bookings separated by {_days(overlap_days)} on the same day is a resourcing problem, not a scheduling problem.",
                    "MEDIUM",
                    f"{_days(overlap_days)} contested",
                ))
                used["split_booking"] += 1
                severity = SEVERITY_CRITICAL
                narrative = (
                    f"{vendor} is double-booked: '{activity_name}' ({_iso(start)} to {_iso(finish)}) overlaps "
                    f"'{other_name}' for {_days(overlap_days)}, but '{activity_name}' only has {_days(total_float)} of "
                    f"float. The clash cannot be scheduled away: {_days(deficit)} has to be resolved by compressing "
                    f"the activity, engaging a second crew, or changing the vendor."
                )
                evidence = _evidence([
                    ("Vendor", str(vendor)),
                    ("Overlap", _days(overlap_days)),
                    ("Total float", _days(total_float)),
                    ("Free float", _days(free_float)),
                    ("Float deficit", _days(deficit)),
                    ("Project impact", f"+{_days(deficit)} days unless resolved"),
                ])

            cards.append(_card(
                severity,
                "VENDOR_OVERBOOKING",
                f"Double-booked: {vendor}",
                narrative,
                evidence=evidence,
                actions=actions,
                activity_ids=[activity_id] + ([other_id] if other_id != "None" else []),
            ))
            continue

        available_from = _iso(conflict.get("available_from"))
        available_to = _iso(conflict.get("available_to"))
        scheduled_start = _iso(conflict.get("scheduled_start"))
        scheduled_finish = _iso(conflict.get("scheduled_finish"))
        raw_recommendation = str(conflict.get("resolution_recommendation", "")).lower()

        if available_from and "before vendor is available" in raw_recommendation:
            days_early = _difference_days(available_from, scheduled_start)
            required = max(0.0, days_early)
            if total_float >= required - float_tolerance_days:
                shift = min(required, total_float)
                new_start = _add_days(scheduled_start, shift)
                actions.append(_action(
                    f"Shift '{activity_name}' {shift:.0f} day(s) later, to start {_iso(new_start)}.",
                    f"Consuming {_days(shift)} of its {_days(total_float)} of float respects the vendor window "
                    f"{_iso(available_from)} to {_iso(available_to)} at no cost to the project date.",
                    "HIGH",
                    f"{_days(shift)} of {_days(total_float)} float",
                ))
                used["float_shift"] += 1
                severity = SEVERITY_WARNING
                narrative = (
                    f"'{activity_name}' is scheduled from {scheduled_start} but {vendor} is only available from "
                    f"{available_from}, {_days(days_early)} too early. The activity has {_days(total_float)} of float, "
                    f"so the start can be pushed to {_iso(new_start)} and the window violation disappears without "
                    f"extending the project."
                )
            else:
                deficit = max(0.0, required - total_float)
                actions.append(_action(
                    f"The {_days(days_early)} vendor wait exceeds the {_days(total_float)} of float by "
                    f"{_days(deficit)}: either crash the activity or bring the vendor forward.",
                    "The constraint is externally imposed, so the only levers are cost or commercial terms.",
                    "HIGH",
                    f"deficit {_days(deficit)}",
                ))
                actions.append(_action(
                    f"Ask {vendor} to open its window {_days(deficit)} earlier.",
                    "Cheaper than crashing the activity when the vendor hold is a soft booking.",
                    "MEDIUM",
                    f"{_days(deficit)}",
                ))
                used["escalate"] += 1
                severity = SEVERITY_CRITICAL
                narrative = (
                    f"'{activity_name}' is scheduled to start on {scheduled_start}, but {vendor} is unavailable until "
                    f"{available_from} and the activity only has {_days(total_float)} of float. The "
                    f"{_days(deficit)} shortfall is unavoidable through scheduling alone: the vendor must open its "
                    f"window earlier or the activity must be compressed."
                )
            cards.append(_card(
                severity,
                "VENDOR_WINDOW_VIOLATION",
                f"Availability clash: {activity_name}",
                narrative,
                evidence=_evidence([
                    ("Vendor", str(vendor)),
                    ("Scheduled start", scheduled_start),
                    ("Vendor available from", available_from),
                    ("Vendor available to", available_to),
                    ("Days too early", _days(days_early)),
                    ("Total float", _days(total_float)),
                    ("Free float", _days(free_float)),
                ]),
                actions=actions,
                activity_ids=[activity_id],
            ))
            continue

        if available_to and "after vendor availability ends" in raw_recommendation:
            days_late = _difference_days(scheduled_finish, available_to)
            actions.append(_action(
                f"Move '{activity_name}' so it finishes by {available_to}, or extend the {vendor} hold by "
                f"{_days(days_late)}.",
                f"The vendor window closes while the activity is still running, so the overrun of {_days(days_late)} "
                f"has to be absorbed by compression, by a partial handover, or by renegotiating the hold.",
                "HIGH",
                f"{_days(days_late)} past window",
            ))
            actions.append(_action(
                f"Only book {vendor} for the days the activity genuinely needs.",
                "Aligning the reservation with the compressed duration prevents a recurring overbooking on the next run.",
                "LOW",
                _days(days_late),
            ))
            used["extend_window"] += 1
            cards.append(_card(
                SEVERITY_CRITICAL,
                "VENDOR_WINDOW_OVERRUN",
                f"Window overrun: {activity_name}",
                (f"'{activity_name}' finishes on {scheduled_finish}, but the {vendor} hold ends on {available_to}, "
                 f"{_days(days_late)} before the crew is released. Float-shifting cannot fix a finish-date clash, "
                 f"because the activity already sits on or near the critical path: the options are to compress the "
                 f"activity, renegotiate the hold, or split the engagement."),
                evidence=_evidence([
                    ("Vendor", str(vendor)),
                    ("Scheduled finish", scheduled_finish),
                    ("Vendor available to", available_to),
                    ("Days past window", _days(days_late)),
                    ("Total float", _days(total_float)),
                ]),
                actions=actions,
                activity_ids=[activity_id],
            ))
            continue

        actions.append(_action(
            f"Review the {vendor} booking for '{activity_name}'.",
            "The availability engine reported a clash that does not match a known pattern, so it needs a human decision.",
            "MEDIUM",
        ))
        cards.append(_card(
            SEVERITY_WARNING,
            "VENDOR_CONFLICT",
            f"Vendor conflict: {activity_name}",
            (f"{vendor} is in conflict with '{activity_name}' (scheduled {scheduled_start} to "
             f"{scheduled_finish}, window {available_from} to {available_to}, float {_days(total_float)}). The raw "
             f"engine recommendation is: {conflict.get('resolution_recommendation', 'n/a')}"),
            evidence=_evidence([
                ("Vendor", str(vendor)),
                ("Scheduled window", f"{scheduled_start} to {scheduled_finish}"),
                ("Vendor window", f"{available_from} to {available_to}"),
                ("Total float", _days(total_float)),
            ]),
            actions=actions,
            activity_ids=[activity_id],
        ))

    if not cards:
        checked = len({str(c.get("activity_id")) for c in conflicts})
        cards.append(_card(
            SEVERITY_SUCCESS,
            "NO_VENDOR_CONFLICTS",
            "All vendor assignments are feasible",
            (f"Every vendor-assigned activity in {label} fits inside its declared availability window and no vendor "
             f"is double-booked. Because the schedule currently sits inside the vendor constraints, all available "
             f"float is genuinely free and can be offered as contingency to the critical path."),
            evidence=_evidence([
                ("Vendors evaluated", str(len({c.get("vendor_name") for c in conflicts if c.get("vendor_name")}))),
                ("Activities with a vendor", "all"),
                ("Window violations", "0"),
                ("Double-bookings", "0"),
            ]),
        ))
        return _vendor_report(label, anchor, cards, 0, used, conflicts, project_start_date)

    vendors = sorted({str(c.get("vendor_name")) for c in conflicts if c.get("vendor_name")})
    float_resolvable = used["float_shift"]
    summary = (
        f"{len(cards)} vendor constraint violation(s) were detected in {label} across {len(vendors)} partner(s). "
        f"{float_resolvable} can be removed purely by shifting float, {used['extend_window'] + used['split_booking']} "
        f"require commercial or structural negotiation, and {used['escalate']} exceed the float available for "
        f"rescheduling. Resolving the float-shift cases first costs zero project days."
    )

    narrative_sentences = [
        f"Conflicts detected: {len(cards)} across {len(vendors)} vendor(s).",
        f"Resolvable by float shift: {float_resolvable}.",
        f"Resolvable by window negotiation: {used['extend_window']}.",
        f"Resolvable by splitting the booking: {used['split_booking']}.",
        f"Requiring escalation: {used['escalate']}.",
    ]

    return _vendor_report(label, anchor, cards, len(cards), used, conflicts, project_start_date,
                          summary=summary, narrative=narrative_sentences, vendors=vendors)


def _vendor_report(
    label: str,
    anchor: Optional[str],
    cards: List[Dict[str, Any]],
    conflict_count: int,
    used: Dict[str, int],
    conflicts: Sequence[Dict[str, Any]],
    project_start_date: Any,
    summary: Optional[str] = None,
    narrative: Optional[List[str]] = None,
    vendors: Optional[List[str]] = None,
) -> Dict[str, Any]:
    checked_vendors = vendors if vendors is not None else sorted(
        {str(c.get("vendor_name")) for c in conflicts if c.get("vendor_name")}
    )
    severity = _highest_severity(cards)
    headline_value = "clear" if conflict_count == 0 else f"{conflict_count} conflict(s)"
    return _report(
        report_type=REPORT_VENDOR,
        title=f"Vendor scheduling explanation for {label}",
        headline={
            "label": "Vendor constraint status",
            "value": headline_value,
            "tone": "success" if conflict_count == 0 else ("critical" if severity == SEVERITY_CRITICAL else "warning"),
        },
        summary=summary or f"No vendor availability conflicts were detected in {label}.",
        narrative=narrative or [f"Vendors evaluated: {len(checked_vendors)}."],
        cards=cards,
        metrics={
            "project_start_date": anchor,
            "conflict_count": conflict_count,
            "vendors_evaluated": len(checked_vendors),
            "float_shift_resolutions": used["float_shift"],
            "window_negotiations": used["extend_window"],
            "split_bookings": used["split_booking"],
            "escalations": used["escalate"],
        },
        evidence_trace=[
            {
                "step": "Calendar projection",
                "method": "Map CPM ES/EF offsets onto the project start date to obtain scheduled windows",
                "inputs": f"Project start {anchor or 'today'}; {len(conflicts)} vendor-assigned activities",
            },
            {
                "step": "Window violation test",
                "method": "scheduled_start < vendor_available_from OR scheduled_finish > vendor_available_to",
                "inputs": f"{used['float_shift'] + used['escalate']} window checks triggered",
            },
            {
                "step": "Overbooking test",
                "method": "Pairwise interval intersection between activities sharing a vendor",
                "inputs": f"{used['split_booking']} overlapping pairs",
            },
            {
                "step": "Float-shift feasibility",
                "method": "required shift <= total float of the activity being moved",
                "inputs": f"{used['float_shift']} of {conflict_count} conflicts resolved without cost to the project date",
            },
        ],
        confidence={
            "level": "HIGH",
            "basis": "Interval arithmetic on deterministic dates; the only assumption is that vendor holds are firm and exclusive.",
        },
    )


def _difference_days(later: Any, earlier: Any) -> float:
    if later is None or earlier is None:
        return 0.0
    try:
        return float((later - earlier).days)
    except (TypeError, AttributeError):
        return 0.0


def _add_days(value: Any, days: float) -> Any:
    if value is None:
        return None
    try:
        from datetime import timedelta
        return value + timedelta(days=int(round(days)))
    except (TypeError, AttributeError, ValueError):
        return value


def _overlap_days(start: Any, finish: Any, other_activity_id: str,
                  conflict: Dict[str, Any], nodes: Dict[str, cpm_engine.ActivityNode],
                  anchor: Optional[str]) -> float:
    other = nodes.get(other_activity_id)
    if other is None:
        return max(1.0, float(conflict.get("total_float", 0.0) or 0.0))
    own_start = _offset_of(start, conflict, nodes, is_start=True)
    own_finish = _offset_of(finish, conflict, nodes, is_start=False)
    overlap_start = max(own_start, other.es)
    overlap_finish = min(own_finish, other.ef)
    return max(0.0, overlap_finish - overlap_start)


def _offset_of(value: Any, conflict: Dict[str, Any],
               nodes: Dict[str, cpm_engine.ActivityNode], is_start: bool) -> float:
    node = nodes.get(str(conflict.get("activity_id")))
    if node is None:
        return 0.0
    anchor_value = conflict.get("scheduled_start") if is_start else conflict.get("scheduled_finish")
    if value is not None and value == anchor_value:
        return node.es if is_start else node.ef
    return node.es if is_start else node.ef


# ---------------------------------------------------------------------------
# Reproducible simulation used to enrich the risk explanation
# ---------------------------------------------------------------------------

def _pert_shape_parameters(optimistic: float, likely: float, pessimistic: float) -> Tuple[float, float]:
    """Beta shape parameters whose mean and mode match the PERT three-point estimate.

    PERT is defined by the expected time ``te = (a + 4m + b) / 6`` and the mode
    ``m``. A Beta distribution on ``[low, high]`` is the standard PERT sampling
    density, but the textbook shortcut ``alpha = 1 + 4r, beta = (2/3) * alpha``
    only matches the mode: its mean is pinned at ``low + 0.6 * (high - low)``,
    which equals ``te`` only when the mode sits at the mid-point. For skewed
    estimates that leaves a systematic offset of up to a sixth of the spread,
    which would be misreported as schedule risk.

    Solving the two moment conditions instead, with the normalised mode
    ``r = (mode - low) / span`` and the normalised expected time
    ``mu = (te - low) / span``::

        alpha / (alpha + beta)      = mu        (mean)
        (alpha - 1) / (a + b - 2)   = r         (mode)

    gives ``S = alpha + beta = (1 - 2r) / (mu - r)``, which is singular when the
    mean and the mode coincide and any symmetric ``alpha = beta > 1`` satisfies
    both conditions. The mean is taken from the raw three points rather than the
    reordered ones so that out-of-order input, where the mode falls outside
    ``[a, b]``, still reproduces the analytic ``te`` the engine reports.
    """
    low = min(optimistic, likely, pessimistic)
    high = max(optimistic, likely, pessimistic)
    span = high - low
    if span < EPS:
        return 1.0, 1.0
    mode = low if not (low <= likely <= high) else likely
    expected_time = (optimistic + 4.0 * likely + pessimistic) / 6.0
    r = min(1.0, max(0.0, (mode - low) / span))
    mu = min(1.0, max(0.0, (expected_time - low) / span))
    if abs(mu - r) < 1e-9:
        return 2.0, 2.0
    total = (1.0 - 2.0 * r) / (mu - r)
    alpha = mu * total
    beta = total - alpha
    if alpha <= 0.0 or beta <= 0.0:
        return 2.0, 2.0
    return alpha, beta


def _pert_sample(activity: Dict[str, Any], rng: random.Random) -> float:
    """Draw one duration from a PERT distribution consistent with the analytic mean."""
    if abs(activity["high"] - activity["low"]) < EPS:
        return activity["mode"]
    unit = rng.betavariate(activity["alpha"], activity["beta"])
    return activity["low"] + unit * (activity["high"] - activity["low"])


def simulate_path_statistics(
    activities: Sequence[Dict[str, Any]],
    num_simulations: int = 1000,
    seed: int = 20260926,
) -> Dict[str, Any]:
    """Seeded Monte Carlo that records per-path statistics for XAI reporting.

    The core engine already reports activity criticality indices; this adds
    path-level means, standard deviations and critical frequencies so the
    near-critical path explanations can be quantitatively justified. A fixed
    seed makes every explanation reproducible.
    """
    prepared = []
    for activity in activities:
        fallback = float(activity.get("duration", 1.0) or 1.0)
        opt = activity.get("optimistic_time")
        likely = activity.get("most_likely_time")
        pess = activity.get("pessimistic_time")
        opt = fallback if opt is None else float(opt)
        likely = opt if likely is None else float(likely)
        pess = likely if pess is None else float(pess)
        low = min(opt, likely, pess)
        high = max(opt, likely, pess)
        mode = low if not (low <= likely <= high) else likely
        alpha, beta = _pert_shape_parameters(opt, likely, pess)
        prepared.append({
            "id": str(activity["id"]),
            "name": activity.get("name", str(activity["id"])),
            "low": low,
            "mode": mode,
            "high": high,
            "alpha": alpha,
            "beta": beta,
            "predecessor_ids": activity.get("predecessor_ids", []) or [],
        })

    if not prepared:
        return {
            "num_simulations": 0,
            "seed": seed,
            "mean_duration": 0.0,
            "std_dev_duration": 0.0,
            "percentiles": {},
            "path_means": {},
            "path_sigmas": {},
            "path_critical_frequencies": {},
            "activity_criticality": {},
            "path_count": 0,
        }

    rng = random.Random(seed)
    trials = max(1, int(num_simulations))
    durations: List[float] = []
    path_sums: Dict[str, float] = {}
    path_squares: Dict[str, float] = {}
    path_counts: Dict[str, int] = {}
    activity_counts: Dict[str, int] = {a["id"]: 0 for a in prepared}

    for _ in range(trials):
        sampled = []
        for activity in prepared:
            duration = _pert_sample(activity, rng)
            sampled.append({
                "id": activity["id"],
                "name": activity["name"],
                "duration": duration,
                "predecessor_ids": activity["predecessor_ids"],
            })
        try:
            _, critical_path, project_duration = cpm_engine.calculate_cpm(sampled)
        except Exception:
            continue
        durations.append(project_duration)
        key = " > ".join(critical_path)
        path_sums[key] = path_sums.get(key, 0.0) + project_duration
        path_squares[key] = path_squares.get(key, 0.0) + project_duration ** 2
        path_counts[key] = path_counts.get(key, 0) + 1
        for activity_id in critical_path:
            if activity_id in activity_counts:
                activity_counts[activity_id] += 1

    if not durations:
        return {
            "num_simulations": 0,
            "seed": seed,
            "mean_duration": 0.0,
            "std_dev_duration": 0.0,
            "percentiles": {},
            "path_means": {},
            "path_sigmas": {},
            "path_critical_frequencies": {},
            "activity_criticality": {},
            "path_count": 0,
        }

    durations.sort()
    n = len(durations)
    mean = sum(durations) / n
    variance = sum((d - mean) ** 2 for d in durations) / n
    mean_standard_error = math.sqrt(variance) / math.sqrt(n) if n > 0 else 0.0

    def percentile(p: float) -> float:
        index = min(n - 1, max(0, int(round(p * (n - 1)))))
        return durations[index]

    path_means: Dict[str, float] = {}
    path_sigmas: Dict[str, float] = {}
    path_frequencies: Dict[str, float] = {}
    for key, total in path_sums.items():
        count = path_counts[key]
        path_mean = total / count
        path_means[key] = round(path_mean, 4)
        path_variance = max(0.0, path_squares[key] / count - path_mean ** 2)
        path_sigmas[key] = round(math.sqrt(path_variance), 4)
        path_frequencies[key] = round(count / n, 4)

    return {
        "num_simulations": n,
        "seed": seed,
        "mean_duration": round(mean, 2),
        "std_dev_duration": round(math.sqrt(variance), 2),
        "mean_standard_error": round(mean_standard_error, 4),
        "min_duration": round(durations[0], 2),
        "max_duration": round(durations[-1], 2),
        "percentiles": {
            "p10": round(percentile(0.10), 2),
            "p50": round(percentile(0.50), 2),
            "p80": round(percentile(0.80), 2),
            "p90": round(percentile(0.90), 2),
            "p95": round(percentile(0.95), 2),
        },
        "path_means": path_means,
        "path_sigmas": path_sigmas,
        "path_critical_frequencies": path_frequencies,
        "activity_criticality": {
            activity_id: round(count / n * 100.0, 2) for activity_id, count in activity_counts.items()
        },
        "path_count": len(path_sums),
    }


# ---------------------------------------------------------------------------
# Portfolio level narrative
# ---------------------------------------------------------------------------

def build_narrative_summary(reports: Sequence[Dict[str, Any]], project_name: Optional[str] = None) -> Dict[str, Any]:
    """Fuse several XAI reports into a single dynamic summary banner."""
    label = project_name or "this project"
    sentences: List[str] = []
    findings: List[str] = []
    actions: List[Dict[str, str]] = []
    severities: List[str] = []

    for report in reports:
        headline = report.get("headline", {})
        if headline.get("value"):
            sentences.append(f"{headline.get('label')}: {headline['value']}.")
        for finding in report.get("high_risk_findings", []):
            findings.append(finding)
        for item in report.get("recommended_actions", []):
            if item not in actions:
                actions.append(item)
        severities.append(report.get("severity", SEVERITY_INFO))

    if not reports:
        return {
            "project_name": label,
            "narrative": ["No XAI analysis is available for this project yet."],
            "severity": SEVERITY_INFO,
            "high_risk_findings": [],
            "recommended_actions": [],
        }

    tone = SEVERITY_INFO
    for level in (SEVERITY_CRITICAL, SEVERITY_WARNING, SEVERITY_SUCCESS, SEVERITY_INFO):
        if level in severities:
            tone = level
            break

    return {
        "project_name": label,
        "narrative": sentences,
        "severity": tone,
        "high_risk_findings": findings,
        "recommended_actions": actions[:6],
    }
