from fastapi import APIRouter

from app.orchestrator.engine import (
    orchestrator_cycles,
    orchestrator_recommendations,
    orchestrator_status,
    orchestrator_telemetry,
    run_orchestration_cycle,
)
from app.orchestrator.schemas import RunCycleRequest


router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.get("/status")
def get_orchestrator_status():
    return orchestrator_status().model_dump()


@router.get("/cycles")
def get_orchestrator_cycles():
    return orchestrator_cycles().model_dump()


@router.get("/recommendations")
def get_orchestrator_recommendations():
    return orchestrator_recommendations().model_dump()


@router.post("/run-cycle")
def run_cycle(request: RunCycleRequest):
    return run_orchestration_cycle(request)


@router.get("/telemetry")
def get_orchestrator_telemetry():
    return orchestrator_telemetry().model_dump()
