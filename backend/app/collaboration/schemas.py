"""
schemas.py — Pydantic request/response schemas for the Collaboration API.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class RunCollaborationRequest(BaseModel):
    """Body for POST /collaboration/run."""

    mission: str = Field(..., description="Mission identifier (e.g. 'seo-growth', 'dashboard-improvement')")
    project_id: str = Field("", description="Project to scope this collaboration to (yallaplays | fionera)")
    proposal_id: str = Field("", description="Optional: tie collaboration to an existing apply-layer proposal")
    proposal_title: str = Field("", description="Optional free-text proposal description for the review record")
    dry_run: bool = Field(False, description="Simulate collaboration without touching apply layer")
    triggered_by: str = Field("api", description="Who initiated this session")
    consensus_threshold: float = Field(75.0, description="Minimum consensus score for approval (0–100)")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AgentRoleResponse(BaseModel):
    agent_name: str
    role: str
    division: str
    specialty: str
    capabilities: list[str]


class ContributionResponse(BaseModel):
    contribution_id: str
    thread_id: str
    session_id: str
    agent_name: str
    role: str
    task: str
    output: str
    score: float
    confidence: float
    simulated: bool
    timestamp: str


class ReviewRecordResponse(BaseModel):
    review_id: str
    thread_id: str
    session_id: str
    reviewer_agent: str
    reviewed_agent: str
    contribution_id: str
    score: float
    approved: bool
    feedback: str
    concerns: list[str]
    role: str
    timestamp: str


class ConsensusScoreResponse(BaseModel):
    consensus_id: str
    session_id: str
    thread_id: str
    individual_scores: dict[str, float]
    role_weights: dict[str, float]
    weighted_score: float
    consensus_score: float
    approved: bool
    threshold: float
    abstentions: list[str]
    score_spread: float
    timestamp: str


class QualityReportResponse(BaseModel):
    report_id: str
    thread_id: str
    session_id: str
    checks_passed: list[str]
    checks_failed: list[str]
    quality_score: float
    approved: bool
    recommendations: list[str]
    reviewer_coverage: float
    validator_independence: bool
    timestamp: str


class ThreadResponse(BaseModel):
    thread_id: str
    session_id: str
    mission: str
    proposal_id: str
    project_id: str
    agents: list[str]
    agent_roles: dict[str, str]
    implementers: list[str]
    reviewers: list[str]
    validators: list[str]
    status: str
    contribution_ids: list[str]
    review_ids: list[str]
    chain_id: str
    consensus_score: float
    quality_score: float
    approved: bool
    conflicts: int
    started_at: str
    completed_at: str
    error: str


class CollaborationSessionResponse(BaseModel):
    session_id: str
    mission: str
    proposal_id: str
    project_id: str
    triggered_by: str
    thread_ids: list[str]
    agents: list[str]
    agent_roles: dict[str, str]
    consensus_score: float
    approved: bool
    review_status: str
    reviewed_by: list[str]
    quality_score: float
    conflicts_detected: int
    conflicts_resolved: int
    started_at: str
    completed_at: str
    status: str
    summary: str
    insights: list[str]


class ThreadListResponse(BaseModel):
    total: int
    threads: list[ThreadResponse]


class ReviewListResponse(BaseModel):
    total: int
    reviews: list[ReviewRecordResponse]


class ConsensusListResponse(BaseModel):
    total: int
    consensus_scores: list[ConsensusScoreResponse]


class QualityListResponse(BaseModel):
    total: int
    reports: list[QualityReportResponse]
