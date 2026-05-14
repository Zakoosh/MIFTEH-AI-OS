"""
api/apply.py — FastAPI router for the Safe Autonomous Apply Layer.

Protected dashboard route: https://yallaplays.com//admin/os

Endpoints:
  POST  /apply/proposal/{proposal_id}   — Run full apply pipeline
  GET   /apply/history                  — List all apply operations
  GET   /apply/previews                 — List all generated previews
  POST  /apply/rollback/{operation_id}  — Rollback an applied operation
  GET   /apply/audit                    — Full audit trail
  GET   /apply/proposals                — List all available proposals
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Body
from typing import Any

from app.apply.proposal_applier import get_applier, list_proposals
from app.apply.schemas import (
    ApplyResponse,
    AuditResponse,
    AuditEntryResponse,
    HistoryResponse,
    PreviewListResponse,
    PreviewResponse,
    ProposalApplyRequest,
    RollbackRequest,
    RollbackResponse,
)

router = APIRouter(prefix="/apply", tags=["Apply Layer"])

_applier = get_applier()


# ---------------------------------------------------------------------------
# POST /apply/proposal/{proposal_id}
# ---------------------------------------------------------------------------

@router.post(
    "/proposal/{proposal_id}",
    response_model=ApplyResponse,
    summary="Apply a proposal by ID",
    description=(
        "Runs the full Safe Apply pipeline: Validate → Preview → Patch → Apply → Audit. "
        "Only low-risk proposals are eligible. Set dry_run=true to simulate without file writes."
    ),
)
def apply_proposal(
    proposal_id: str,
    body: ProposalApplyRequest = Body(default=ProposalApplyRequest()),
) -> ApplyResponse:
    try:
        result = _applier.apply(proposal_id, dry_run=body.dry_run)
        return ApplyResponse(**result.to_dict())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /apply/history
# ---------------------------------------------------------------------------

@router.get(
    "/history",
    response_model=HistoryResponse,
    summary="List all apply operations",
    description="Returns all apply results ordered by most recent first.",
)
def apply_history() -> HistoryResponse:
    try:
        operations = _applier.history()
        return HistoryResponse(total=len(operations), operations=operations)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /apply/previews
# ---------------------------------------------------------------------------

@router.get(
    "/previews",
    response_model=PreviewListResponse,
    summary="List all generated previews",
    description="Returns all proposal previews that have been generated.",
)
def apply_previews() -> PreviewListResponse:
    try:
        raw = _applier.previews()
        previews = []
        for item in raw:
            try:
                previews.append(PreviewResponse(**item))
            except Exception:
                pass
        return PreviewListResponse(total=len(previews), previews=previews)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# POST /apply/rollback/{operation_id}
# ---------------------------------------------------------------------------

@router.post(
    "/rollback/{operation_id}",
    response_model=RollbackResponse,
    summary="Rollback an applied operation",
    description=(
        "Restores the file state from the backup created before the apply. "
        "Each operation can only be rolled back once."
    ),
)
def rollback_operation(
    operation_id: str,
    body: RollbackRequest = Body(default=RollbackRequest()),
) -> RollbackResponse:
    try:
        result = _applier.rollback(operation_id, reason=body.reason)
        return RollbackResponse(
            operation_id=result.get("operation_id", operation_id),
            proposal_id=result.get("proposal_id", ""),
            restored=result.get("restored", False),
            message=result.get("message", ""),
            timestamp=result.get("timestamp", ""),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /apply/audit
# ---------------------------------------------------------------------------

@router.get(
    "/audit",
    response_model=AuditResponse,
    summary="Full audit trail",
    description="Returns all audit entries across every apply operation.",
)
def apply_audit() -> AuditResponse:
    try:
        raw = _applier.audit()
        entries = []
        for item in raw:
            try:
                entries.append(AuditEntryResponse(**item))
            except Exception:
                pass
        return AuditResponse(total=len(entries), entries=entries)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /apply/proposals
# ---------------------------------------------------------------------------

@router.get(
    "/proposals",
    summary="List all available proposals",
    description="Returns all built-in and stored proposals from the registry.",
)
def get_proposals() -> dict[str, Any]:
    try:
        proposals = list_proposals()
        return {
            "total": len(proposals),
            "proposals": proposals,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ---------------------------------------------------------------------------
# GET /apply/proposals/{proposal_id}
# ---------------------------------------------------------------------------

@router.get(
    "/proposals/{proposal_id}",
    summary="Get a single proposal",
    description="Returns a single proposal from the registry by its ID.",
)
def get_proposal(proposal_id: str) -> dict[str, Any]:
    from app.apply.proposal_applier import get_proposal as _get
    proposal = _get(proposal_id)
    if proposal is None:
        raise HTTPException(status_code=404, detail=f"Proposal '{proposal_id}' not found")
    return proposal.to_dict()


# ---------------------------------------------------------------------------
# GET /apply/status
# ---------------------------------------------------------------------------

@router.get(
    "/status",
    summary="Apply Layer health status",
    description="Returns operational status and metrics for the Apply Layer.",
)
def apply_status() -> dict[str, Any]:
    try:
        history = _applier.history()
        audit = _applier.audit()
        previews = _applier.previews()
        proposals = list_proposals()

        applied_count = sum(1 for h in history if h.get("applied"))
        rollback_count = sum(1 for h in history if not h.get("rollback_available") and h.get("applied"))

        return {
            "status": "operational",
            "layer": "Safe Autonomous Apply Layer",
            "version": "1.0.0",
            "protected_dashboard": "https://yallaplays.com//admin/os",
            "metrics": {
                "total_proposals": len(proposals),
                "total_operations": len(history),
                "applied_operations": applied_count,
                "rolled_back_operations": rollback_count,
                "audit_entries": len(audit),
                "previews_generated": len(previews),
            },
            "projects": ["yallaplays", "fionera"],
            "policy": {
                "max_risk_level": "low",
                "preview_required": True,
                "patch_required": True,
                "rollback_supported": True,
                "audit_enabled": True,
                "unsafe_overwrite": False,
                "production_deployment": False,
            },
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
