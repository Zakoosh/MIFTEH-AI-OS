from app.intelligence.analyzer import intelligence_overview
from app.orchestrator.cycle_manager import build_orchestration_cycle
from app.orchestrator.mission_loop import build_recommendation_loop
from app.orchestrator.models import (
    IMPROVEMENT_AREAS,
    ORCHESTRATION_MODE_ADVISORY,
    OrchestrationCycleList,
    OrchestratorRecommendationList,
    OrchestratorStatus,
)
from app.orchestrator.schemas import RunCycleRequest
from app.orchestrator.telemetry import build_telemetry, load_cycles


SAFEGUARDS = [
    "rule_based_only",
    "no_autonomous_code_application",
    "no_auto_merge",
    "no_git_push",
    "cooldown_enforced",
    "repeated_failure_prevention",
    "manual_review_for_blocked_missions",
]


def orchestrator_status() -> OrchestratorStatus:
    cycles = load_cycles()
    telemetry = build_telemetry(cycles)

    try:
        overview = intelligence_overview()
        projects_count = overview.projects_count
    except Exception:
        projects_count = 0

    latest = cycles[0] if cycles else None

    return OrchestratorStatus(
        status="ready",
        mode=ORCHESTRATION_MODE_ADVISORY,
        safe_operations_only=True,
        projects_monitored=projects_count,
        latest_cycle_id=latest.cycle_id if latest else None,
        latest_cycle_at=latest.completed_at if latest else None,
        recommendations_count=telemetry.recommendations_total,
        blocked_count=telemetry.blocked_total,
        improvement_areas=IMPROVEMENT_AREAS.copy(),
        safeguards=SAFEGUARDS,
    )


def orchestrator_cycles() -> OrchestrationCycleList:
    return OrchestrationCycleList(cycles=load_cycles())


def orchestrator_recommendations() -> OrchestratorRecommendationList:
    return OrchestratorRecommendationList(
        recommendations=build_recommendation_loop(
            previous_cycles=load_cycles(),
            include_blocked=True,
        )
    )


def run_orchestration_cycle(request: RunCycleRequest) -> dict:
    try:
        cycle = build_orchestration_cycle(
            dry_run=request.dry_run,
            max_missions=request.max_missions,
            include_blocked=request.include_blocked,
            persist=True,
        )
        return {
            "success": True,
            "cycle": cycle.model_dump(),
            "message": "Orchestration cycle planned. No missions were executed.",
        }
    except Exception as exc:
        return {
            "success": False,
            "error": str(exc),
        }


def orchestrator_telemetry():
    return build_telemetry(load_cycles())
