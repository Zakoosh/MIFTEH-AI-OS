from __future__ import annotations
from fastapi import APIRouter, Query
from ..runtime.runtime_engine import RuntimeEngine
from ..runtime.models import OperationType, RuntimeMode
from ..runtime.schemas import (
    RuntimeStatusResponse, OperationsListResponse, AnalyticsResponse,
    RunRequest, RunResponse, RuntimeHealthResponse,
)

router = APIRouter(prefix="/runtime", tags=["runtime"])
engine = RuntimeEngine()


@router.get("/status", response_model=RuntimeStatusResponse)
async def get_status():
    return RuntimeStatusResponse(**engine.get_status())


@router.get("/operations", response_model=OperationsListResponse)
async def list_operations(
    project: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    ops = engine.get_operations(project=project, status=status, limit=limit)
    active = len([o for o in ops if o.get("status") in ("running", "queued")])
    completed = len([o for o in ops if o.get("status") == "completed"])
    failed = len([o for o in ops if o.get("status") == "failed"])
    return OperationsListResponse(
        operations=ops,
        total=len(ops),
        active=active,
        completed=completed,
        failed=failed,
    )


@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics(period: str = Query("24h")):
    data = engine.get_analytics(period)
    return AnalyticsResponse(**data)


@router.post("/run", response_model=RunResponse)
async def run_cycle(request: RunRequest):
    try:
        op_type = OperationType(request.operation_type) if isinstance(request.operation_type, str) else request.operation_type
        mode = RuntimeMode(request.mode) if isinstance(request.mode, str) else request.mode
    except ValueError as e:
        return RunResponse(success=False, message=str(e), blocked_by="validation")

    result = engine.run(
        project=request.project,
        mode=mode,
        operation_type=op_type,
        trust_score=request.trust_score,
    )
    return RunResponse(
        success=result.get("success", False),
        operation_id=result.get("operation_id"),
        cycle_id=result.get("cycle_id"),
        message=result.get("message", result.get("error", "")),
        blocked_by=result.get("blocked_by"),
    )


@router.get("/health", response_model=RuntimeHealthResponse)
async def get_health():
    return RuntimeHealthResponse(**engine.get_health())
