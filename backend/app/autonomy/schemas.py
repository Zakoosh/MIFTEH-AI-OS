"""
schemas.py — Pydantic request/response schemas for the Autonomy API.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RunCycleRequest(BaseModel):
    """Optional body for POST /autonomy/run-cycle."""

    dry_run: bool = Field(False, description="Simulate the cycle without writing files")
    max_proposals: int = Field(0, description="Override max_per_cycle (0 = use config default)")
    project_filter: str = Field("", description="Restrict cycle to a single project_id")
    triggered_by: str = Field("api", description="Who triggered this cycle")


class ConfigUpdateRequest(BaseModel):
    """Optional body for updating autonomy config."""

    enabled: bool | None = None
    dry_run_mode: bool | None = None
    trust_threshold: float | None = None
    rollback_threshold: float | None = None
    max_per_cycle: int | None = None
    max_per_day: int | None = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class TrustScoreResponse(BaseModel):
    key: str
    project_id: str
    proposal_type: str
    trust_score: float          # renamed from score for API clarity
    apply_count: int
    success_count: int
    failure_count: int
    rollback_count: int
    rollback_rate: float
    autonomous_apply_allowed: bool
    suspended: bool
    suspension_reason: str
    last_updated: str


class TrustListResponse(BaseModel):
    total: int
    trust_scores: list[TrustScoreResponse]


class OutcomeResponse(BaseModel):
    outcome_id: str
    operation_id: str
    proposal_id: str
    project_id: str
    proposal_type: str
    outcome: str
    simulated: bool
    dry_run: bool
    timestamp: str
    details: dict[str, Any]


class OutcomeListResponse(BaseModel):
    total: int
    outcomes: list[OutcomeResponse]


class CycleResponse(BaseModel):
    cycle_id: str
    triggered_by: str
    dry_run: bool
    started_at: str
    completed_at: str
    proposals_evaluated: int
    proposals_selected: int
    proposals_applied: int
    proposals_skipped: int
    outcome_ids: list[str]
    trust_updates: dict[str, Any]
    status: str
    error: str
    summary: str


class CycleListResponse(BaseModel):
    total: int
    cycles: list[CycleResponse]


class AutonomyStatusResponse(BaseModel):
    status: str
    layer: str
    version: str
    protected_dashboard: str
    enabled: bool
    dry_run_mode: bool
    config: dict[str, Any]
    metrics: dict[str, Any]
    trust_summary: dict[str, Any]
    projects: list[str]
    policy: dict[str, Any]


class RiskGateResponse(BaseModel):
    proposal_id: str
    proposal_type: str
    project_id: str
    allowed: bool
    trust_score: float
    rollback_rate: float
    reasons_blocked: list[str]
    reasons_allowed: list[str]
