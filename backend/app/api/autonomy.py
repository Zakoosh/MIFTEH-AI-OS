"""
api/autonomy.py — FastAPI router for the Autonomous Operational Loops Layer.

Protected dashboard route: yallaplays.com/admin/os

Endpoints:
  GET   /autonomy/status         — Engine status, config, metrics
  GET   /autonomy/trust          — Trust scores per proposal type
  GET   /autonomy/cycles         — Cycle history
  POST  /autonomy/run-cycle      — Trigger an autonomous cycle
  GET   /autonomy/outcomes       — All outcome records

Additional endpoints:
  GET   /autonomy/feedback       — Feedback/learning entries
  GET   /autonomy/limits         — Hard limits summary
  GET   /autonomy/eligibility    — Proposal eligibility evaluation
  POST  /autonomy/config         — Update engine configuration
  GET   /autonomy/analytics      — Aggregated operational analytics
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Body

from app.autonomy.autonomous_engine import get_engine, load_config, save_config
from app.autonomy.autonomy_cycles import get_cycle_manager
from app.autonomy.outcome_tracker import get_tracker
from app.autonomy.feedback_loop import get_feedback_loop
from app.autonomy.trust_scores import get_trust_manager
from app.autonomy.proposal_selector import get_selector
from app.autonomy.safety_limits import get_limits_summary
from app.autonomy.schemas import (
    RunCycleRequest,
    ConfigUpdateRequest,
    AutonomyStatusResponse,
    TrustListResponse,
    TrustScoreResponse,
    CycleListResponse,
    CycleResponse,
    OutcomeListResponse,
    OutcomeResponse,
)

router = APIRouter(prefix="/autonomy", tags=["Autonomy Layer"])

_engine = get_engine()
_cycles = get_cycle_manager()
_tracker = get_tracker()
_feedback = get_feedback_loop()
_trust = get_trust_manager()
_selector = get_selector()


# ---------------------------------------------------------------------------
# GET /autonomy/status
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    summary="Autonomy engine status",
    description=(
        "Returns full operational status of the Autonomous Loops Layer, "
        "including config, cycle metrics, outcome metrics, and trust summary."
    ),
)
def autonomy_status() -> dict[str, Any]:
    try:
        return _engine.get_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /autonomy/trust
# ---------------------------------------------------------------------------

@router.get(
    "/trust",
    response_model=TrustListResponse,
    summary="Trust scores per proposal type",
    description=(
        "Returns trust scores for all tracked (project_id, proposal_type) pairs. "
        "Example: seo_metadata trust=92 → autonomous_apply_allowed=true"
    ),
)
def autonomy_trust() -> TrustListResponse:
    try:
        config = load_config()

        # Seed defaults so all known types appear even without prior runs
        _trust.seed_defaults(
            initial_score=config.initial_trust_score,
            trust_threshold=config.trust_threshold,
            rollback_threshold=config.rollback_threshold,
        )

        scores = _trust.list_all(config.trust_threshold, config.rollback_threshold)
        responses = []
        for ts in scores:
            d = ts.to_dict()
            d["trust_score"] = d.pop("score")   # rename score → trust_score for API
            try:
                responses.append(TrustScoreResponse(**d))
            except Exception:
                pass
        return TrustListResponse(total=len(responses), trust_scores=responses)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /autonomy/cycles
# ---------------------------------------------------------------------------

@router.get(
    "/cycles",
    response_model=CycleListResponse,
    summary="Autonomy cycle history",
    description="Returns all autonomy cycles ordered by most recent first.",
)
def autonomy_cycles() -> CycleListResponse:
    try:
        all_cycles = _cycles.list_all()
        responses = []
        for c in all_cycles:
            try:
                responses.append(CycleResponse(**c.to_dict()))
            except Exception:
                pass
        return CycleListResponse(total=len(responses), cycles=responses)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /autonomy/run-cycle
# ---------------------------------------------------------------------------

@router.post(
    "/run-cycle",
    response_model=CycleResponse,
    summary="Trigger an autonomous cycle",
    description=(
        "Runs one bounded autonomous operational cycle. "
        "Selects, validates, and applies eligible low-risk proposals. "
        "Set dry_run=true to simulate without writing files."
    ),
)
def run_autonomy_cycle(
    body: RunCycleRequest = Body(default=RunCycleRequest()),
) -> CycleResponse:
    try:
        cycle = _engine.run_cycle(
            triggered_by=body.triggered_by,
            dry_run=body.dry_run,
            max_proposals=body.max_proposals,
            project_filter=body.project_filter,
        )
        return CycleResponse(**cycle.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /autonomy/outcomes
# ---------------------------------------------------------------------------

@router.get(
    "/outcomes",
    response_model=OutcomeListResponse,
    summary="All operation outcomes",
    description="Returns all autonomous apply outcomes ordered by most recent first.",
)
def autonomy_outcomes() -> OutcomeListResponse:
    try:
        all_outcomes = _tracker.list_all()
        responses = []
        for o in all_outcomes:
            try:
                responses.append(OutcomeResponse(**o.to_dict()))
            except Exception:
                pass
        return OutcomeListResponse(total=len(responses), outcomes=responses)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /autonomy/feedback
# ---------------------------------------------------------------------------

@router.get(
    "/feedback",
    summary="Feedback and learning entries",
    description="Returns all feedback loop entries that drove trust score changes.",
)
def autonomy_feedback() -> dict[str, Any]:
    try:
        entries = _feedback.list_all()
        return {
            "total": len(entries),
            "entries": [e.to_dict() for e in entries],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /autonomy/limits
# ---------------------------------------------------------------------------

@router.get(
    "/limits",
    summary="Hard safety limits",
    description="Returns the non-negotiable hard limits for the autonomy engine.",
)
def autonomy_limits() -> dict[str, Any]:
    try:
        return {
            "limits": get_limits_summary(),
            "description": (
                "These limits are enforced regardless of config settings. "
                "They represent the absolute ceiling on autonomous behavior."
            ),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /autonomy/eligibility
# ---------------------------------------------------------------------------

@router.get(
    "/eligibility",
    summary="Proposal eligibility evaluation",
    description="Evaluates all proposals and returns their eligibility for autonomous apply.",
)
def autonomy_eligibility(project: str = "") -> dict[str, Any]:
    try:
        config = load_config()
        return _selector.evaluate_all(config=config, project_filter=project)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /autonomy/config
# ---------------------------------------------------------------------------

@router.post(
    "/config",
    summary="Update autonomy configuration",
    description=(
        "Partially update the autonomy engine configuration. "
        "Hard limits still apply regardless of what is set here."
    ),
)
def update_autonomy_config(
    body: ConfigUpdateRequest = Body(default=ConfigUpdateRequest()),
) -> dict[str, Any]:
    try:
        updated = _engine.update_config(
            enabled=body.enabled,
            dry_run_mode=body.dry_run_mode,
            trust_threshold=body.trust_threshold,
            rollback_threshold=body.rollback_threshold,
            max_per_cycle=body.max_per_cycle,
            max_per_day=body.max_per_day,
        )
        return {
            "updated": True,
            "config": updated.to_dict(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /autonomy/analytics
# ---------------------------------------------------------------------------

@router.get(
    "/analytics",
    summary="Aggregated operational analytics",
    description=(
        "Returns rich analytics: trust by type, outcomes by type, "
        "rollback analytics, and cycle performance metrics."
    ),
)
def autonomy_analytics() -> dict[str, Any]:
    try:
        config = load_config()

        # Trust scores
        trust_scores = _trust.list_all(config.trust_threshold, config.rollback_threshold)

        # Outcome aggregations
        by_type = _tracker.aggregate_by_type()
        by_project = _tracker.aggregate_by_project()
        overall = _tracker.overall_metrics()

        # Cycle metrics
        cycle_metrics = _cycles.cycle_metrics()

        # Build per-type trust + outcome combined view
        combined: list[dict] = []
        for ts in trust_scores:
            key = f"{ts.project_id}:{ts.proposal_type}"
            outcome_data = by_type.get(key, {})
            combined.append({
                "proposal_type": ts.proposal_type,
                "project_id": ts.project_id,
                "trust_score": ts.score,
                "autonomous_apply_allowed": ts.autonomous_apply_allowed,
                "rollback_rate": ts.rollback_rate,
                "suspended": ts.suspended,
                "apply_count": ts.apply_count,
                "success_count": ts.success_count,
                "rollback_count": ts.rollback_count,
                "outcome_rollback_rate": outcome_data.get("rollback_rate", 0.0),
                "outcome_success_rate": outcome_data.get("success_rate", 0.0),
            })

        # Rollback analytics
        rollback_risk = sorted(
            [t for t in combined if t["rollback_rate"] > 0],
            key=lambda x: x["rollback_rate"],
            reverse=True,
        )

        # AI operational insights
        insights = _build_insights(trust_scores, overall, cycle_metrics)

        return {
            "overall_metrics": overall,
            "cycle_metrics": cycle_metrics,
            "by_project": by_project,
            "by_type": by_type,
            "trust_and_outcomes": combined,
            "rollback_risk_ranking": rollback_risk,
            "operational_insights": insights,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


def _build_insights(trust_scores: list, overall: dict, cycle_metrics: dict) -> list[str]:
    """Generate AI operational insights for the analytics endpoint."""
    insights = []

    if not trust_scores:
        insights.append("No trust scores tracked yet. Run the first cycle to begin learning.")
        return insights

    avg_trust = sum(ts.score for ts in trust_scores) / len(trust_scores)
    insights.append(f"Average trust score across all types: {avg_trust:.1f}/100.")

    suspended = [ts for ts in trust_scores if ts.suspended]
    if suspended:
        types = [f"{ts.project_id}:{ts.proposal_type}" for ts in suspended]
        insights.append(f"WARNING: {len(suspended)} type(s) suspended due to high rollback rate: {', '.join(types)}.")

    high_trust = [ts for ts in trust_scores if ts.score >= 90]
    if high_trust:
        insights.append(
            f"{len(high_trust)} type(s) with trust >= 90: "
            + ", ".join(f"{ts.proposal_type}({ts.score:.0f})" for ts in high_trust)
        )

    rollback_rate = overall.get("overall_rollback_rate", 0)
    if rollback_rate > 15:
        insights.append(
            f"ALERT: Overall rollback rate {rollback_rate:.1f}% is elevated. "
            "Review recent apply operations."
        )
    elif rollback_rate == 0 and overall.get("total_operations", 0) > 0:
        insights.append("Zero rollbacks recorded — apply operations are performing well.")

    if cycle_metrics.get("total_cycles", 0) == 0:
        insights.append("No autonomous cycles have been run yet.")
    else:
        insights.append(
            f"Total cycles: {cycle_metrics['total_cycles']}, "
            f"total applied: {cycle_metrics['total_applied']}."
        )

    return insights
