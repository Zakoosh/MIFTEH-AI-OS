"""
dependency_graph.py — Builds dependency graphs for work items.

Combines explicit dependencies (from WorkItem.dependencies) with
inferred relationships based on task_type ordering rules.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from .models import (
    DependencyNode, DependencyEdge, DependencyGraph,
    REL_REQUIRES, REL_BLOCKS, REL_ENHANCES,
)


# ---------------------------------------------------------------------------
# Inference rules
# key   → task type that REQUIRES the value types to be done first
# ---------------------------------------------------------------------------

_INFERRED_DEPS: dict[str, list[str]] = {
    "seo_campaign":   ["implementation"],          # CDN / perf must be ready
    "feature":        ["implementation"],
    "dashboard":      ["feature", "widget"],
    "widget":         ["feature"],
    "analytics":      ["feature", "dashboard"],
    "watchlist":      ["feature"],
    "monetization":   ["feature"],
    "optimization":   ["feature", "ux"],
    "ux":             [],
    "implementation": [],
    "roadmap":        [],
    "campaign":       ["seo_campaign"],
    "content":        [],
}

# Items of this type should be executed first (lower layer number)
_LAYER: dict[str, int] = {
    "implementation": 0,
    "roadmap":        0,
    "ux":             1,
    "seo_campaign":   1,
    "content":        1,
    "feature":        2,
    "campaign":       2,
    "widget":         3,
    "watchlist":      3,
    "dashboard":      4,
    "analytics":      4,
    "optimization":   4,
    "monetization":   4,
}


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build_graph(items: list[Any], project: str = "all") -> DependencyGraph:
    """
    Build a DependencyGraph from a list of WorkItem-like objects.
    Combines explicit .dependencies with inferred type-level deps.
    """
    # Index by item_id
    by_id: dict[str, Any] = {i.item_id: i for i in items}

    # --- nodes ---
    nodes: list[DependencyNode] = []
    for item in items:
        nodes.append(DependencyNode(
            node_id          = item.item_id,
            project          = item.project,
            title            = item.title,
            task_type        = item.task_type,
            priority         = item.priority,
            estimated_days   = item.estimated_days,
            dependency_layer = _LAYER.get(item.task_type, 2),
        ))

    # --- edges (explicit) ---
    edges: list[DependencyEdge] = []
    seen: set[tuple[str, str]] = set()

    for item in items:
        for dep_id in (item.dependencies or []):
            if dep_id in by_id and (dep_id, item.item_id) not in seen:
                edges.append(DependencyEdge(
                    from_id      = dep_id,
                    to_id        = item.item_id,
                    relationship = REL_REQUIRES,
                    inferred     = False,
                ))
                seen.add((dep_id, item.item_id))

    # --- edges (inferred) ---
    # Group items by task_type
    by_type: dict[str, list[str]] = defaultdict(list)
    for item in items:
        by_type[item.task_type].append(item.item_id)

    for item in items:
        required_types = _INFERRED_DEPS.get(item.task_type, [])
        for req_type in required_types:
            for dep_item_id in by_type.get(req_type, []):
                if dep_item_id != item.item_id and (dep_item_id, item.item_id) not in seen:
                    edges.append(DependencyEdge(
                        from_id      = dep_item_id,
                        to_id        = item.item_id,
                        relationship = REL_REQUIRES,
                        inferred     = True,
                    ))
                    seen.add((dep_item_id, item.item_id))

    # --- add enhance edges for items of the same type ---
    for type_items in by_type.values():
        for i in range(1, len(type_items)):
            a, b = type_items[i - 1], type_items[i]
            if (a, b) not in seen:
                edges.append(DependencyEdge(
                    from_id      = a,
                    to_id        = b,
                    relationship = REL_ENHANCES,
                    inferred     = True,
                ))
                seen.add((a, b))

    critical = _compute_critical_path(nodes, edges, by_id)
    cp_ids   = {n for n in critical}
    for e in edges:
        if e.from_id in cp_ids and e.to_id in cp_ids:
            e.critical_path = True

    order = _topological_groups(nodes, edges)

    graph = DependencyGraph(
        graph_id              = f"dep_{project}_{len(items)}",
        project               = project,
        nodes                 = [n.to_dict() for n in nodes],
        edges                 = [e.to_dict() for e in edges],
        critical_path         = critical,
        execution_order       = order,
        total_nodes           = len(nodes),
        total_edges           = len(edges),
        critical_path_length  = len(critical),
    )
    return graph


# ---------------------------------------------------------------------------
# Critical path (longest dependency chain by estimated_days)
# ---------------------------------------------------------------------------

def _compute_critical_path(
    nodes: list[DependencyNode],
    edges: list[DependencyEdge],
    by_id: dict[str, Any],
) -> list[str]:
    # Build adjacency: id → list of successors
    successors: dict[str, list[str]] = defaultdict(list)
    predecessors: dict[str, list[str]] = defaultdict(list)
    for e in edges:
        if e.relationship == REL_REQUIRES:
            successors[e.from_id].append(e.to_id)
            predecessors[e.to_id].append(e.from_id)

    node_ids = {n.node_id for n in nodes}
    days     = {n.node_id: n.estimated_days for n in nodes}

    # Longest path (DAG DP)
    dist: dict[str, float] = {nid: 0.0 for nid in node_ids}
    prev: dict[str, str | None] = {nid: None for nid in node_ids}

    # Topological order
    in_deg = {nid: len(predecessors[nid]) for nid in node_ids}
    queue  = deque(nid for nid in node_ids if in_deg[nid] == 0)
    topo: list[str] = []
    while queue:
        u = queue.popleft()
        topo.append(u)
        for v in successors[u]:
            in_deg[v] -= 1
            if in_deg[v] == 0:
                queue.append(v)

    for u in topo:
        for v in successors[u]:
            new_dist = dist[u] + days.get(v, 0)
            if new_dist > dist[v]:
                dist[v] = new_dist
                prev[v] = u

    if not dist:
        return []

    end = max(dist, key=lambda k: dist[k])
    path: list[str] = []
    cur: str | None = end
    while cur is not None:
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()
    return path


# ---------------------------------------------------------------------------
# Topological sort into parallel execution groups
# ---------------------------------------------------------------------------

def _topological_groups(
    nodes: list[DependencyNode],
    edges: list[DependencyEdge],
) -> list[list[str]]:
    """Return layers of nodes that can be executed in parallel."""
    requires_edges = [e for e in edges if e.relationship == REL_REQUIRES]
    in_deg: dict[str, int] = {n.node_id: 0 for n in nodes}
    successors: dict[str, list[str]] = defaultdict(list)

    for e in requires_edges:
        in_deg[e.to_id] = in_deg.get(e.to_id, 0) + 1
        successors[e.from_id].append(e.to_id)

    groups: list[list[str]] = []
    remaining = set(in_deg.keys())

    while remaining:
        layer = [nid for nid in remaining if in_deg[nid] == 0]
        if not layer:
            # cycle — add rest as a single group
            groups.append(list(remaining))
            break
        # sort by priority within layer (critical first)
        priority_map = {n.node_id: n.dependency_layer for n in nodes}
        layer.sort(key=lambda nid: priority_map.get(nid, 99))
        groups.append(layer)
        for nid in layer:
            remaining.discard(nid)
            for succ in successors[nid]:
                in_deg[succ] -= 1

    return groups
