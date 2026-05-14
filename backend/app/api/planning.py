"""
api/planning.py — FastAPI router for the Autonomous Execution Planning Layer.

Protected dashboard route: yallaplays.com/admin/os

Required endpoints:
  GET /planning/execution     — Execution plans for work items
  GET /planning/dependencies  — Dependency graph
  GET /planning/milestones    — Strategic milestones
  GET /planning/rollouts      — Phased rollout plans
  GET /planning/tracking      — Delivery tracking report

Additional endpoints:
  GET /planning/status        — Layer status and analytics
  GET /planning/validation    — Validation sequences
  GET /planning/effort        — Effort estimates
  GET /planning/analytics     — Full planning analytics
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query

from app.planning.execution_planner import get_planner
from app.planning.schemas import (
    ExecutionListResponse,
    ExecutionPlanSchema,
    DependenciesResponse,
    DependencyGraphResponse,
    MilestonesResponse,
    MilestoneSchema,
    RolloutsResponse,
    RolloutPlanSchema,
    TrackingResponse,
    DeliveryCheckpointSchema,
)

router = APIRouter(prefix="/planning", tags=["Planning Layer"])

_planner = get_planner()


# ---------------------------------------------------------------------------
# GET /planning/execution
# ---------------------------------------------------------------------------

@router.get(
    "/execution",
    response_model=ExecutionListResponse,
    summary="Execution plans for work items",
    description=(
        "Returns implementation-grade execution plans for every work item. "
        "Each plan contains ordered steps, phase assignments, agent roles, "
        "and validation checkpoints."
    ),
)
def get_execution(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
    task_types: list[str] = Query(default=[], description="Filter by task type"),
    limit: int = Query(default=50, description="Maximum plans to return"),
) -> ExecutionListResponse:
    try:
        plans = _planner.plan_all(project)
        if task_types:
            plans = [p for p in plans if p.task_type in task_types]
        plans = plans[:limit]

        total_days    = sum(p.estimated_days for p in plans)
        total_hours   = sum(p.estimated_hours for p in plans)
        steps_total   = sum(len(p.steps) for p in plans)
        avg_steps     = round(steps_total / len(plans), 1) if plans else 0.0
        by_phase: dict[str, int] = {}
        for p in plans:
            for ph in p.phases:
                by_phase[ph] = by_phase.get(ph, 0) + 1

        critical = [
            p.plan_id for p in plans if p.priority == "critical"
        ]

        summary = {
            "total_estimated_days":  total_days,
            "total_estimated_hours": round(total_hours, 1),
            "avg_steps_per_plan":    avg_steps,
            "by_phase":              by_phase,
            "critical_items":        critical,
        }

        return ExecutionListResponse(
            project          = project,
            total            = len(plans),
            plans            = [ExecutionPlanSchema(**p.to_dict()) for p in plans],
            execution_summary= summary,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /planning/dependencies
# ---------------------------------------------------------------------------

@router.get(
    "/dependencies",
    response_model=DependenciesResponse,
    summary="Dependency graph",
    description=(
        "Returns a full dependency graph for all work items including "
        "explicit and inferred relationships, critical path, and execution order."
    ),
)
def get_dependencies(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
) -> DependenciesResponse:
    try:
        graph = _planner.get_dependency_graph(project)
        return DependenciesResponse(
            project = project,
            graph   = DependencyGraphResponse(**graph.to_dict()),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /planning/milestones
# ---------------------------------------------------------------------------

@router.get(
    "/milestones",
    response_model=MilestonesResponse,
    summary="Strategic milestones",
    description=(
        "Returns strategic delivery milestones grouped by quarter. "
        "Each milestone maps to a set of work items with success criteria and deliverables."
    ),
)
def get_milestones(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
    quarter: str = Query(default="", description="Filter by quarter, e.g. 'Q3-2026'"),
) -> MilestonesResponse:
    try:
        milestones = _planner.get_milestones(project)
        if quarter:
            milestones = [m for m in milestones if m.quarter == quarter]

        by_quarter: dict[str, list[MilestoneSchema]] = {}
        responses: list[MilestoneSchema] = []
        for m in milestones:
            schema = MilestoneSchema(**m.to_dict())
            responses.append(schema)
            by_quarter.setdefault(m.quarter, []).append(schema)

        return MilestonesResponse(
            total      = len(responses),
            by_quarter = by_quarter,
            milestones = responses,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /planning/rollouts
# ---------------------------------------------------------------------------

@router.get(
    "/rollouts",
    response_model=RolloutsResponse,
    summary="Phased rollout plans",
    description=(
        "Returns phased rollout plans per project and quarter. "
        "Each plan contains phase bands with work items, timing, exit criteria, "
        "and rollback triggers."
    ),
)
def get_rollouts(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
    quarter: str = Query(default="", description="Filter by quarter"),
) -> RolloutsResponse:
    try:
        rollouts = _planner.get_rollout_plans(project)
        if quarter:
            rollouts = [r for r in rollouts if r.quarter == quarter]

        return RolloutsResponse(
            total   = len(rollouts),
            rollouts= [RolloutPlanSchema(**r.to_dict()) for r in rollouts],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /planning/tracking
# ---------------------------------------------------------------------------

@router.get(
    "/tracking",
    response_model=TrackingResponse,
    summary="Delivery tracking report",
    description=(
        "Returns delivery status for all execution plans: on_track, at_risk, "
        "delayed, completed — with health score and actionable insights."
    ),
)
def get_tracking(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
) -> TrackingResponse:
    try:
        report = _planner.get_delivery_report(project)
        checkpoints = [
            DeliveryCheckpointSchema(**cp)
            for cp in report.checkpoints
        ]
        return TrackingResponse(
            project       = report.project,
            total_plans   = report.total_plans,
            on_track      = report.on_track,
            at_risk       = report.at_risk,
            delayed       = report.delayed,
            completed     = report.completed,
            overall_health= report.overall_health,
            health_score  = report.health_score,
            checkpoints   = checkpoints,
            insights      = report.insights,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /planning/status
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    summary="Planning layer status",
    description="Returns full operational status and summary analytics.",
)
def planning_status() -> dict[str, Any]:
    try:
        return _planner.get_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /planning/validation
# ---------------------------------------------------------------------------

@router.get(
    "/validation",
    summary="Validation sequences",
    description="Returns ordered validation checklists for all work items.",
)
def get_validation(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
) -> dict[str, Any]:
    try:
        seqs = _planner.get_validation_sequences(project)
        return {
            "total":   len(seqs),
            "sequences": [s.to_dict() for s in seqs],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /planning/effort
# ---------------------------------------------------------------------------

@router.get(
    "/effort",
    summary="Effort estimates",
    description=(
        "Returns detailed effort estimates per work item: raw days, complexity "
        "factor, risk buffer, total days, per-phase breakdown, and confidence level."
    ),
)
def get_effort(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
) -> dict[str, Any]:
    try:
        estimates = _planner.get_effort_estimates(project)
        total     = sum(e.total_days for e in estimates)
        return {
            "total_items":       len(estimates),
            "total_effort_days": round(total, 1),
            "estimates":         [e.to_dict() for e in estimates],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /planning/analytics
# ---------------------------------------------------------------------------

@router.get(
    "/analytics",
    summary="Full planning analytics",
    description=(
        "Returns aggregated planning analytics: plan counts, effort totals, "
        "critical path, top effort items, and breakdowns by project / type / priority."
    ),
)
def planning_analytics() -> dict[str, Any]:
    try:
        return _planner.get_analytics().to_dict()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
