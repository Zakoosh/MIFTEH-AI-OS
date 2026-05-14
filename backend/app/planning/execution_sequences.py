"""
execution_sequences.py — Computes phased, dependency-aware execution ordering.

Takes a dependency graph and produces a flat list of item IDs in safe
execution order, plus a phase grouping for parallel execution.
"""

from __future__ import annotations

from typing import Any

from .models import (
    ExecutionPhase, ExecutionPlan,
    PHASE_PREPARATION, PHASE_IMPLEMENTATION, PHASE_REVIEW,
    PHASE_DEPLOYMENT, PHASE_VALIDATION,
)
from .dependency_graph import build_graph


# ---------------------------------------------------------------------------
# Phase assignment by task type
# ---------------------------------------------------------------------------

_TASK_PHASE: dict[str, str] = {
    "implementation": PHASE_PREPARATION,
    "roadmap":        PHASE_PREPARATION,
    "ux":             PHASE_PREPARATION,
    "seo_campaign":   PHASE_IMPLEMENTATION,
    "content":        PHASE_IMPLEMENTATION,
    "feature":        PHASE_IMPLEMENTATION,
    "campaign":       PHASE_IMPLEMENTATION,
    "widget":         PHASE_REVIEW,
    "watchlist":      PHASE_REVIEW,
    "dashboard":      PHASE_REVIEW,
    "analytics":      PHASE_REVIEW,
    "optimization":   PHASE_DEPLOYMENT,
    "monetization":   PHASE_DEPLOYMENT,
}


# ---------------------------------------------------------------------------
# Phase band definitions for rollout grouping
# phase_band → (start_offset_days, duration_days, title, description)
# ---------------------------------------------------------------------------

_PHASE_BANDS = [
    (0,  14, "Foundation",           "Infrastructure, technical debt, and UX groundwork"),
    (14, 21, "Core Implementation",  "Primary features, SEO clusters, and key workflows"),
    (35, 21, "Enhancement",          "Supporting widgets, watchlists, analytics, and dashboards"),
    (56, 14, "Optimisation & Launch","A/B tests, monetisation, and final production rollout"),
]


def compute_execution_order(items: list[Any]) -> list[str]:
    """Return a flat ordered list of item IDs (dependencies before dependants)."""
    graph = build_graph(items)
    order: list[str] = []
    for group in graph.execution_order:
        order.extend(group)
    return order


def phase_label_for(task_type: str) -> str:
    return _TASK_PHASE.get(task_type, PHASE_IMPLEMENTATION)


def group_items_into_bands(
    items: list[Any],
    project: str,
    quarter: str,
    rollout_id: str,
) -> list[ExecutionPhase]:
    """
    Assign work items to one of four execution phase bands.
    Returns a list of ExecutionPhase objects.
    """
    layer_map: dict[str, int] = {
        "implementation": 0, "roadmap": 0,
        "ux": 0,
        "seo_campaign": 1, "content": 1, "feature": 1, "campaign": 1,
        "widget": 2, "watchlist": 2, "dashboard": 2, "analytics": 2,
        "optimization": 3, "monetization": 3,
    }

    bands: dict[int, list[str]] = {0: [], 1: [], 2: [], 3: []}
    for item in items:
        band = layer_map.get(item.task_type, 1)
        bands[band].append(item.item_id)

    phases: list[ExecutionPhase] = []
    for band_idx, (start, dur, title, desc) in enumerate(_PHASE_BANDS):
        item_ids = bands.get(band_idx, [])
        if not item_ids:
            continue
        phase_id = f"ph_{project}_{quarter}_p{band_idx + 1}"
        phases.append(ExecutionPhase(
            phase_id         = phase_id,
            rollout_id       = rollout_id,
            phase_number     = band_idx + 1,
            title            = title,
            description      = desc,
            work_item_ids    = item_ids,
            plan_ids         = [f"plan_{wid}" for wid in item_ids],
            start_offset_days= start,
            duration_days    = dur,
            exit_criteria    = _exit_criteria_for(band_idx),
            rollback_trigger = _rollback_trigger_for(band_idx),
            milestone_ids    = [],
        ))
    return phases


def _exit_criteria_for(band: int) -> list[str]:
    criteria = {
        0: [
            "All infrastructure components pass health checks",
            "CI pipeline green on main branch",
            "No P0/P1 bugs open",
        ],
        1: [
            "All features pass acceptance criteria",
            "SEO pages indexed by Google Search Console",
            "Unit test coverage ≥ 80%",
            "Staging environment validated",
        ],
        2: [
            "All widgets and dashboards pass QA sign-off",
            "Performance budget met (Lighthouse ≥ 85)",
            "Zero critical security findings",
        ],
        3: [
            "A/B tests conclude with statistical significance",
            "Monetisation flows tested end-to-end in staging",
            "Production deployment without incident",
            "Post-launch monitoring active for 48 h",
        ],
    }
    return criteria.get(band, ["All acceptance criteria met"])


def _rollback_trigger_for(band: int) -> str:
    triggers = {
        0: "Error rate > 1% or latency > 2× baseline on infrastructure components",
        1: "Feature error rate > 0.5% or critical business metric regression > 10%",
        2: "Dashboard data accuracy error or P0 bug in widget",
        3: "Checkout failure rate > 0.1% or revenue metric regression > 15%",
    }
    return triggers.get(band, "Any P0 incident post-deploy")
