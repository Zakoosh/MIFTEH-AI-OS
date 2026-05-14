"""
rollout_executor.py — Executes phased rollout plans from the Planning Layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from . import delivery_memory as mem
from .models import _sim_success, _sim_score, _now, DELIVERY_COMPLETED


def execute_rollout(project: str, quarter: str = "Q3-2026", dry_run: bool = True) -> dict[str, Any]:
    """
    Simulate execution of a rollout plan for the given project + quarter.
    Returns a rollout execution result dict.
    """
    from app.planning.execution_planner import get_planner

    planner   = get_planner()
    rollouts  = planner.get_rollout_plans(project)
    target    = next((r for r in rollouts if r.quarter == quarter), None)

    if target is None:
        return {"error": f"No rollout plan for {project}/{quarter}"}

    rollout_id = f"roex_{project}_{quarter.replace('-', '_').lower()}"
    phases_done: list[dict] = []
    all_passed   = True
    total_items  = target.total_work_items
    delivered    = 0

    for i, phase_dict in enumerate(target.phases):
        phase_name  = phase_dict.get("title", f"Phase {i+1}")
        item_ids    = phase_dict.get("work_item_ids", [])
        seed        = f"{rollout_id}_{phase_name}"
        phase_ok    = _sim_success(seed, 0.94)
        health      = _sim_score(seed, 86.0, 14.0)
        items_done  = len(item_ids) if phase_ok else max(0, len(item_ids) - 1)
        delivered  += items_done

        phases_done.append({
            "phase_number":     phase_dict.get("phase_number", i + 1),
            "title":            phase_name,
            "status":           DELIVERY_COMPLETED if phase_ok else "failed",
            "work_item_ids":    item_ids,
            "items_delivered":  items_done,
            "health_score":     health,
            "exit_criteria_met": phase_ok,
            "duration_days":    phase_dict.get("duration_days", 14),
            "dry_run":          dry_run,
        })
        if not phase_ok:
            all_passed = False

    result = {
        "rollout_id":              rollout_id,
        "project":                 project,
        "quarter":                 quarter,
        "title":                   target.title,
        "total_phases":            len(phases_done),
        "total_work_items":        total_items,
        "items_delivered":         delivered,
        "delivery_rate_pct":       round(delivered / max(total_items, 1) * 100, 1),
        "all_phases_passed":       all_passed,
        "overall_health":          "good" if all_passed else "caution",
        "dry_run":                 dry_run,
        "simulated":               True,
        "phases":                  phases_done,
        "executed_at":             _now(),
        "validation_passed":       all_passed,
        "rollback_ready":          True,
        "deployment_preview_generated": True,
    }
    mem.save_rollout(result)
    return result


def list_rollout_executions() -> list[dict[str, Any]]:
    stored = mem.list_rollouts()
    if stored:
        return stored

    # Seed with simulated results for all known project+quarter combos
    seeds = [
        ("yallaplays", "Q3-2026"),
        ("yallaplays", "Q4-2026"),
        ("fionera",    "Q3-2026"),
        ("fionera",    "Q4-2026"),
    ]
    results = []
    for proj, q in seeds:
        r = execute_rollout(proj, q, dry_run=True)
        if "error" not in r:
            results.append(r)
    return results
