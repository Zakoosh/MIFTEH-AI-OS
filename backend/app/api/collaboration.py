"""
api/collaboration.py — FastAPI router for the Multi-Agent Collaborative Execution Layer.

Protected dashboard route: yallaplays.com/admin/os

Endpoints:
  GET   /collaboration/threads       — All execution threads
  GET   /collaboration/reviews       — All review records
  GET   /collaboration/consensus     — All consensus scores
  POST  /collaboration/run           — Trigger a new collaborative session
  GET   /collaboration/quality       — All quality reports

Additional endpoints:
  GET   /collaboration/status        — Layer status and metrics
  GET   /collaboration/sessions      — All completed sessions
  GET   /collaboration/missions      — Available mission types
  GET   /collaboration/conflicts     — Detected conflict records
  GET   /collaboration/analytics     — Rich collaboration analytics
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, HTTPException, Body

from app.collaboration.collaboration_engine import get_engine
from app.collaboration.execution_threads import get_thread_manager
from app.collaboration.review_chain import get_review_chain_builder
from app.collaboration.consensus import get_consensus_engine
from app.collaboration.quality_control import get_quality_controller
from app.collaboration.conflict_resolution import get_conflict_resolver
from app.collaboration.collaboration_memory import get_collaboration_memory
from app.collaboration.agent_roles import get_all_missions, list_mission_names
from app.collaboration.schemas import (
    RunCollaborationRequest,
    CollaborationSessionResponse,
    ThreadListResponse,
    ThreadResponse,
    ReviewListResponse,
    ReviewRecordResponse,
    ConsensusListResponse,
    ConsensusScoreResponse,
    QualityListResponse,
    QualityReportResponse,
)

router = APIRouter(prefix="/collaboration", tags=["Collaboration Layer"])

_engine   = get_engine()
_threads  = get_thread_manager()
_review   = get_review_chain_builder()
_consensus = get_consensus_engine()
_qc       = get_quality_controller()
_conflicts = get_conflict_resolver()
_memory   = get_collaboration_memory()


# ---------------------------------------------------------------------------
# GET /collaboration/threads
# ---------------------------------------------------------------------------

@router.get(
    "/threads",
    response_model=ThreadListResponse,
    summary="All execution threads",
    description="Returns all multi-agent execution threads ordered by most recent first.",
)
def get_threads() -> ThreadListResponse:
    try:
        all_t = _threads.list_all()
        responses = []
        for t in all_t:
            try:
                responses.append(ThreadResponse(**t.to_dict()))
            except Exception:
                pass
        return ThreadListResponse(total=len(responses), threads=responses)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /collaboration/reviews
# ---------------------------------------------------------------------------

@router.get(
    "/reviews",
    response_model=ReviewListResponse,
    summary="All review records",
    description=(
        "Returns all reviewer and validator review records. "
        "Example: reviewed_by=['product-manager', 'testing-performance-benchmarker']"
    ),
)
def get_reviews() -> ReviewListResponse:
    try:
        all_r = _review.list_all_reviews()
        responses = []
        for r in all_r:
            try:
                responses.append(ReviewRecordResponse(**r.to_dict()))
            except Exception:
                pass
        return ReviewListResponse(total=len(responses), reviews=responses)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /collaboration/consensus
# ---------------------------------------------------------------------------

@router.get(
    "/consensus",
    response_model=ConsensusListResponse,
    summary="All consensus scores",
    description=(
        "Returns consensus scores for all collaboration sessions. "
        "Example: consensus_score=87, approved=true"
    ),
)
def get_consensus() -> ConsensusListResponse:
    try:
        all_c = _consensus.list_all()
        responses = []
        for c in all_c:
            try:
                responses.append(ConsensusScoreResponse(**c.to_dict()))
            except Exception:
                pass
        return ConsensusListResponse(total=len(responses), consensus_scores=responses)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /collaboration/run
# ---------------------------------------------------------------------------

@router.post(
    "/run",
    response_model=CollaborationSessionResponse,
    summary="Trigger a collaborative session",
    description=(
        "Runs a full multi-agent collaborative execution session for the given mission. "
        "Selects agents, distributes roles, runs review chain, computes consensus, "
        "resolves conflicts, and applies quality control. "
        "Example missions: seo-growth, dashboard-improvement, category-optimization."
    ),
)
def run_collaboration(
    body: RunCollaborationRequest = Body(...),
) -> CollaborationSessionResponse:
    try:
        session = _engine.run_session(
            mission=body.mission,
            project_id=body.project_id,
            proposal_id=body.proposal_id,
            proposal_title=body.proposal_title,
            triggered_by=body.triggered_by,
            consensus_threshold=body.consensus_threshold,
            dry_run=body.dry_run,
        )
        return CollaborationSessionResponse(**session.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /collaboration/quality
# ---------------------------------------------------------------------------

@router.get(
    "/quality",
    response_model=QualityListResponse,
    summary="All quality reports",
    description="Returns all quality control reports from completed collaboration sessions.",
)
def get_quality() -> QualityListResponse:
    try:
        all_qr = _qc.list_all()
        responses = []
        for qr in all_qr:
            try:
                responses.append(QualityReportResponse(**qr.to_dict()))
            except Exception:
                pass
        return QualityListResponse(total=len(responses), reports=responses)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /collaboration/status
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    summary="Layer status and metrics",
    description="Returns full operational status of the Collaboration Layer.",
)
def collaboration_status() -> dict[str, Any]:
    try:
        return _engine.get_status()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /collaboration/sessions
# ---------------------------------------------------------------------------

@router.get(
    "/sessions",
    summary="All collaboration sessions",
    description="Returns all completed and running collaboration sessions.",
)
def get_sessions() -> dict[str, Any]:
    try:
        sessions = _memory.list_sessions_as_dicts()
        return {"total": len(sessions), "sessions": sessions}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /collaboration/sessions/{session_id}
# ---------------------------------------------------------------------------

@router.get(
    "/sessions/{session_id}",
    summary="Get a single collaboration session",
)
def get_session(session_id: str) -> dict[str, Any]:
    session = _memory.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found")
    return session.to_dict()


# ---------------------------------------------------------------------------
# GET /collaboration/missions
# ---------------------------------------------------------------------------

@router.get(
    "/missions",
    summary="Available collaboration mission types",
    description="Returns all defined collaboration missions with their agent rosters.",
)
def get_missions() -> dict[str, Any]:
    try:
        missions = get_all_missions()
        return {
            "total": len(missions),
            "missions": {
                name: {
                    "description":   m["description"],
                    "project_type":  m["project_type"],
                    "implementers":  m.get("implementers", []),
                    "reviewers":     m.get("reviewers", []),
                    "validators":    m.get("validators", []),
                }
                for name, m in missions.items()
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /collaboration/conflicts
# ---------------------------------------------------------------------------

@router.get(
    "/conflicts",
    summary="Detected conflict records",
    description="Returns all detected conflicts and their resolution status.",
)
def get_conflicts() -> dict[str, Any]:
    try:
        all_c = _conflicts.list_all()
        return {
            "total": len(all_c),
            "unresolved": sum(1 for c in all_c if not c.resolved),
            "conflicts": [c.to_dict() for c in all_c],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /collaboration/analytics
# ---------------------------------------------------------------------------

@router.get(
    "/analytics",
    summary="Rich collaboration analytics",
    description=(
        "Returns detailed analytics: session metrics, mission breakdown, "
        "agent activity, consensus analytics, quality analytics, and insights."
    ),
)
def collaboration_analytics() -> dict[str, Any]:
    try:
        sessions         = _memory.list_sessions()
        metrics          = _memory.session_metrics()
        breakdown        = _memory.mission_breakdown()
        activity         = _memory.agent_activity()
        consensus_stats  = _consensus.analytics()
        quality_stats    = _qc.analytics()
        insights         = _memory.generate_insights(sessions)
        conflict_count   = len(_conflicts.list_all())
        unresolved       = _conflicts.count_unresolved()

        return {
            "session_metrics":        metrics,
            "mission_breakdown":      breakdown,
            "agent_activity":         activity,
            "consensus_analytics":    consensus_stats,
            "quality_analytics":      quality_stats,
            "conflict_summary": {
                "total":      conflict_count,
                "unresolved": unresolved,
                "resolved":   conflict_count - unresolved,
            },
            "operational_insights":   insights,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
