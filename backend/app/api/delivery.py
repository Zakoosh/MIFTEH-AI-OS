"""
api/delivery.py — FastAPI router for the Autonomous Delivery Execution Layer.

Protected dashboard route: yallaplays.com/admin/os

Required endpoints:
  GET  /delivery/plans               — All delivery plans
  GET  /delivery/phases              — Phase execution summaries
  GET  /delivery/rollouts            — Rollout execution results
  POST /delivery/execute/{plan_id}   — Execute a delivery plan
  GET  /delivery/health              — Delivery health report

Additional endpoints:
  GET  /delivery/status              — Layer status
  GET  /delivery/runs                — All stored execution runs
  GET  /delivery/runs/{run_id}       — Single run detail
  GET  /delivery/previews            — Deployment previews
  GET  /delivery/analytics           — Delivery analytics
  GET  /delivery/audit               — Audit trail
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Query, Body

from app.delivery.delivery_engine import get_engine
from app.delivery.rollout_executor import list_rollout_executions, execute_rollout
from app.delivery import delivery_memory as mem
from app.delivery.schemas import (
    ExecuteRequest,
    DeliveryPlanSchema,
    DeliveryRunSchema,
    DeliveryHealthSchema,
    PlansListResponse,
    PhasesResponse,
    RolloutsResponse,
)

router  = APIRouter(prefix="/delivery", tags=["Delivery Layer"])
_engine = get_engine()


# ---------------------------------------------------------------------------
# GET /delivery/plans
# ---------------------------------------------------------------------------

@router.get(
    "/plans",
    response_model=PlansListResponse,
    summary="All delivery plans",
    description=(
        "Returns delivery plans for every work item across both projects. "
        "Each plan shows execution status, phases, and latest run info."
    ),
)
def get_plans(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
) -> PlansListResponse:
    try:
        plans = _engine.list_delivery_plans(project)
        return PlansListResponse(
            project = project,
            total   = len(plans),
            plans   = [DeliveryPlanSchema(**p.to_dict()) for p in plans],
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /delivery/phases
# ---------------------------------------------------------------------------

@router.get(
    "/phases",
    response_model=PhasesResponse,
    summary="Phase execution summaries",
    description=(
        "Returns per-phase execution summaries from all stored runs. "
        "Shows step counts, validation results, and rollback availability per phase."
    ),
)
def get_phases(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
) -> PhasesResponse:
    try:
        phases = _engine.get_phases_summary(project)
        return PhasesResponse(
            project      = project,
            total_phases = len(phases),
            phases       = phases,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /delivery/rollouts
# ---------------------------------------------------------------------------

@router.get(
    "/rollouts",
    response_model=RolloutsResponse,
    summary="Rollout execution results",
    description=(
        "Returns rollout execution results per project and quarter. "
        "Each entry shows phase delivery rates, health scores, and validation status."
    ),
)
def get_rollouts(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
    quarter: str = Query(default="", description="Filter by quarter, e.g. 'Q3-2026'"),
) -> RolloutsResponse:
    try:
        rollouts = list_rollout_executions()
        if project != "all":
            rollouts = [r for r in rollouts if r.get("project") == project]
        if quarter:
            rollouts = [r for r in rollouts if r.get("quarter") == quarter]
        return RolloutsResponse(total=len(rollouts), rollouts=rollouts)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /delivery/execute/{plan_id}
# ---------------------------------------------------------------------------

@router.post(
    "/execute/{plan_id}",
    response_model=DeliveryRunSchema,
    summary="Execute a delivery plan",
    description=(
        "Executes a delivery plan end-to-end: phases, validation checkpoints, "
        "collaborative session, deployment preview, and rollback readiness. "
        "Always dry_run=true by default (no live deployment). "
        "plan_id format: 'plan_wi_yp_001', 'plan_wi_fi_001', etc."
    ),
)
def execute_plan(
    plan_id: str,
    body: ExecuteRequest = Body(default=ExecuteRequest()),
) -> DeliveryRunSchema:
    try:
        run = _engine.execute_plan(
            plan_id      = plan_id,
            dry_run      = body.dry_run,
            triggered_by = body.triggered_by,
            force        = body.force,
        )
        return DeliveryRunSchema(**run.to_dict())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /delivery/health
# ---------------------------------------------------------------------------

@router.get(
    "/health",
    response_model=DeliveryHealthSchema,
    summary="Delivery health report",
    description=(
        "Returns delivery health: run counts, avg health score, "
        "validation pass rate, rollback rate, and actionable insights."
    ),
)
def get_health(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
) -> DeliveryHealthSchema:
    try:
        report = _engine.get_health(project)
        return DeliveryHealthSchema(**report.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /delivery/status
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    summary="Delivery layer status",
)
def delivery_status() -> dict[str, Any]:
    try:
        return _engine.get_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /delivery/runs
# ---------------------------------------------------------------------------

@router.get(
    "/runs",
    summary="All stored execution runs",
)
def get_runs(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
) -> dict[str, Any]:
    try:
        runs = mem.list_runs()
        if project != "all":
            runs = [r for r in runs if r.get("project") == project]
        return {"total": len(runs), "runs": runs}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /delivery/runs/{run_id}
# ---------------------------------------------------------------------------

@router.get(
    "/runs/{run_id}",
    summary="Single execution run detail",
)
def get_run(run_id: str) -> dict[str, Any]:
    run = mem.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return run


# ---------------------------------------------------------------------------
# GET /delivery/previews
# ---------------------------------------------------------------------------

@router.get(
    "/previews",
    summary="Deployment previews",
    description="Returns generated deployment previews showing affected files and pages.",
)
def get_previews(
    project: str = Query(default="all", description="'yallaplays' | 'fionera' | 'all'"),
) -> dict[str, Any]:
    try:
        previews = mem.list_previews()
        if project != "all":
            previews = [p for p in previews if p.get("project") == project]
        return {"total": len(previews), "previews": previews}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /delivery/analytics
# ---------------------------------------------------------------------------

@router.get(
    "/analytics",
    summary="Delivery analytics",
    description=(
        "Returns aggregated delivery analytics: run counts, health scores, "
        "validation pass rates, recovery counts, and phase completion rates."
    ),
)
def delivery_analytics() -> dict[str, Any]:
    try:
        return _engine.get_analytics()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /delivery/audit
# ---------------------------------------------------------------------------

@router.get(
    "/audit",
    summary="Delivery audit trail",
    description="Returns the full audit trail of delivery actions.",
)
def get_audit(
    plan_id: str = Query(default="", description="Filter by plan_id"),
) -> dict[str, Any]:
    try:
        entries = mem.list_audit(plan_id)
        return {"total": len(entries), "entries": entries}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
