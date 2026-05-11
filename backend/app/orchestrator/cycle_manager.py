from datetime import datetime, timezone

from app.intelligence.analyzer import intelligence_overview
from app.orchestrator.execution_policy import base_execution_constraints, normalized_max_missions
from app.orchestrator.mission_loop import build_recommendation_loop
from app.orchestrator.models import (
    ORCHESTRATION_STATUS_BLOCKED,
    ORCHESTRATION_STATUS_PLANNED,
    OrchestrationCycle,
)
from app.orchestrator.telemetry import load_cycles, save_cycle


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cycle_id() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    return f"orchestration_cycle_{timestamp}"


def build_orchestration_cycle(
    dry_run: bool = True,
    max_missions: int = 5,
    include_blocked: bool = False,
    persist: bool = True,
) -> OrchestrationCycle:
    started_at = _now()
    constraints = base_execution_constraints(dry_run=dry_run)
    previous_cycles = load_cycles()
    max_count = normalized_max_missions(max_missions)
    recommendations = build_recommendation_loop(
        previous_cycles=previous_cycles,
        include_blocked=include_blocked,
    )
    selected = recommendations[:max_count]
    blocked_count = sum(1 for recommendation in selected if recommendation.blocked)
    has_blocking_cycle_constraint = any(not constraint.allowed for constraint in constraints)

    notes = [
        "Cycle is planning-only and does not execute missions.",
        "Projects are treated as living systems that require continuous optimization.",
        "Scheduler actions are recommendations for approved follow-up workflows.",
    ]

    try:
        overview = intelligence_overview()
        projects_evaluated = overview.projects_count
    except Exception:
        projects_evaluated = 0
        notes.append("Intelligence overview was unavailable during cycle creation.")

    cycle = OrchestrationCycle(
        cycle_id=_cycle_id(),
        status=ORCHESTRATION_STATUS_BLOCKED if has_blocking_cycle_constraint else ORCHESTRATION_STATUS_PLANNED,
        started_at=started_at,
        completed_at=_now(),
        dry_run=dry_run,
        projects_evaluated=projects_evaluated,
        recommendations_count=len(selected),
        blocked_count=blocked_count,
        selected_recommendations=selected,
        constraints=constraints,
        notes=notes,
    )

    if persist:
        save_cycle(cycle)

    return cycle
