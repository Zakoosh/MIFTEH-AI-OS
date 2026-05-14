"""
schemas.py — Pydantic request/response schemas for the Apply API.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ProposalApplyRequest(BaseModel):
    """Optional body when triggering a proposal apply."""

    force_preview: bool = Field(False, description="Force regeneration of preview even if cached")
    dry_run: bool = Field(False, description="Run full pipeline but skip the final file write")


class RollbackRequest(BaseModel):
    """Optional body for rollback endpoint."""

    reason: str = Field("", description="Human-readable reason for the rollback")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ValidationResultResponse(BaseModel):
    proposal_id: str
    valid: bool
    risk_level: str
    checks_passed: list[str]
    checks_failed: list[str]
    warnings: list[str]
    message: str


class PreviewResponse(BaseModel):
    proposal_id: str
    operation_type: str
    target_file: str
    before_summary: str
    after_summary: str
    changes_count: int
    simulated: bool
    generated_at: str


class ApplyResponse(BaseModel):
    proposal_id: str
    operation_id: str
    project: str
    validated: bool
    preview_generated: bool
    patch_generated: bool
    applied: bool
    rollback_available: bool
    simulated: bool
    message: str
    details: dict[str, Any]
    timestamp: str


class RollbackResponse(BaseModel):
    operation_id: str
    proposal_id: str
    restored: bool
    message: str
    timestamp: str


class AuditEntryResponse(BaseModel):
    audit_id: str
    operation_id: str
    proposal_id: str
    project_id: str
    action: str
    status: str
    actor: str
    timestamp: str
    details: dict[str, Any]


class HistoryResponse(BaseModel):
    total: int
    operations: list[dict[str, Any]]


class AuditResponse(BaseModel):
    total: int
    entries: list[AuditEntryResponse]


class PreviewListResponse(BaseModel):
    total: int
    previews: list[PreviewResponse]
