"""
delivery_tracking.py — Generates delivery checkpoints and health reports.

Status is computed deterministically from item attributes so the layer
works offline without a live database.
"""

from __future__ import annotations

from typing import Any

from .models import (
    DeliveryCheckpoint, DeliveryReport,
    DELIVERY_ON_TRACK, DELIVERY_AT_RISK, DELIVERY_DELAYED, DELIVERY_COMPLETED,
)
from .effort_estimator import estimate


# ---------------------------------------------------------------------------
# Status derivation
# ---------------------------------------------------------------------------

def _derive_status(item: Any, est_total_days: float) -> str:
    """
    Deterministic status from item attributes:
    - critical + high complexity  → at_risk
    - critical + very high effort → delayed
    - otherwise                   → on_track
    """
    if item.priority == "critical" and est_total_days >= 25:
        return DELIVERY_DELAYED
    if item.priority == "critical":
        return DELIVERY_AT_RISK
    if item.priority == "high" and est_total_days >= 20:
        return DELIVERY_AT_RISK
    return DELIVERY_ON_TRACK


def _completion_pct(status: str, priority: str) -> float:
    if status == DELIVERY_COMPLETED:
        return 100.0
    if status == DELIVERY_DELAYED:
        return 10.0
    if status == DELIVERY_AT_RISK:
        return 25.0 if priority == "critical" else 30.0
    # on_track
    if priority == "critical":
        return 45.0
    if priority == "high":
        return 50.0
    return 60.0


def _blockers_for(item: Any, status: str) -> list[str]:
    if status == DELIVERY_DELAYED:
        return [
            "Pending dependency resolution",
            "Resource allocation not confirmed",
        ]
    if status == DELIVERY_AT_RISK:
        return ["Complexity estimate revised upward"]
    return []


def _notes_for(item: Any, status: str) -> str:
    msgs = {
        DELIVERY_DELAYED:   "Item flagged for scope review; dependencies need re-evaluation.",
        DELIVERY_AT_RISK:   "On watch-list; may need additional engineering resource.",
        DELIVERY_ON_TRACK:  "Progressing as planned.",
        DELIVERY_COMPLETED: "Delivered and verified.",
    }
    return msgs.get(status, "")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_checkpoints(plans: list[Any]) -> list[DeliveryCheckpoint]:
    """Create one DeliveryCheckpoint per plan, using effort estimates for timing."""
    checkpoints: list[DeliveryCheckpoint] = []

    # Import here to avoid circular deps at module load time
    from app.workgen.yallaplays_workgen import get_yallaplays_work_items
    from app.workgen.fionera_workgen import get_fionera_work_items

    item_map: dict[str, Any] = {
        i.item_id: i
        for i in get_yallaplays_work_items() + get_fionera_work_items()
    }

    for plan in plans:
        item = item_map.get(plan.work_item_id)
        if item is None:
            continue
        est       = estimate(item)
        status    = _derive_status(item, est.total_days)
        pct       = _completion_pct(status, item.priority)
        blockers  = _blockers_for(item, status)
        notes     = _notes_for(item, status)

        checkpoints.append(DeliveryCheckpoint(
            checkpoint_id          = f"cp_{plan.work_item_id}",
            plan_id                = plan.plan_id,
            work_item_id           = plan.work_item_id,
            project                = plan.project,
            title                  = plan.title,
            target_days_from_start = int(est.total_days),
            completion_percentage  = pct,
            status                 = status,
            blockers               = blockers,
            notes                  = notes,
            priority               = plan.priority,
            estimated_days         = plan.estimated_days,
        ))

    return checkpoints


def build_delivery_report(
    project: str,
    plans: list[Any],
) -> DeliveryReport:
    checkpoints = build_checkpoints(plans)

    on_track  = sum(1 for c in checkpoints if c.status == DELIVERY_ON_TRACK)
    at_risk   = sum(1 for c in checkpoints if c.status == DELIVERY_AT_RISK)
    delayed   = sum(1 for c in checkpoints if c.status == DELIVERY_DELAYED)
    completed = sum(1 for c in checkpoints if c.status == DELIVERY_COMPLETED)
    total     = len(checkpoints)

    # Proportional score: penalise as percentage of total
    at_risk_pct  = (at_risk  / total * 100) if total else 0.0
    delayed_pct  = (delayed  / total * 100) if total else 0.0
    health_score = max(0.0, 100.0 - (at_risk_pct * 0.8) - (delayed_pct * 2.0))
    if health_score >= 80:
        health = "good"
    elif health_score >= 60:
        health = "caution"
    else:
        health = "critical"

    insights: list[str] = []
    if delayed:
        insights.append(
            f"{delayed} item(s) delayed — review scope or resource allocation."
        )
    if at_risk:
        insights.append(
            f"{at_risk} item(s) at risk — monitor closely and consider de-scoping."
        )
    if on_track == total:
        insights.append("All items on track. Maintain current velocity.")
    if health == "good" and at_risk == 0:
        insights.append("Delivery health is excellent.")

    return DeliveryReport(
        report_id     = f"rep_{project}",
        project       = project,
        total_plans   = total,
        on_track      = on_track,
        at_risk       = at_risk,
        delayed       = delayed,
        completed     = completed,
        overall_health= health,
        health_score  = round(health_score, 1),
        checkpoints   = [c.to_dict() for c in checkpoints],
        insights      = insights,
    )
