"""
schemas.py — Pydantic request/response schemas for the Delivery Layer API.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request
# ---------------------------------------------------------------------------

class ExecuteRequest(BaseModel):
    dry_run: bool = Field(True, description="Simulate execution without live deployment")
    triggered_by: str = Field("autonomous", description="Who triggered this execution")
    force: bool = Field(False, description="Re-execute even if a run already exists")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class DeliveryPlanSchema(BaseModel):
    plan_id: str
    work_item_id: str
    project: str
    title: str
    description: str
    task_type: str
    priority: str
    phases: list[str]
    total_steps: int
    total_estimated_hours: float
    validation_required: bool
    rollback_available: bool
    dependencies: list[str]
    source_quarter: str
    latest_run_id: str
    total_runs: int
    created_at: str
    status: str


class DeliveryRunSchema(BaseModel):
    run_id: str
    plan_id: str
    work_item_id: str
    project: str
    title: str
    triggered_by: str
    dry_run: bool
    simulated: bool
    current_phase: str
    phases_completed: list[str]
    phases_remaining: list[str]
    completed_steps: int
    total_steps: int
    remaining_steps: int
    health_score: float
    validation_passed: bool
    rollback_ready: bool
    deployment_preview_generated: bool
    recovery_actions: list[Any]
    phases: list[Any]
    checkpoints: list[Any]
    collaborative_session_id: str
    started_at: str
    completed_at: str
    status: str
    error: str


class DeliveryPhaseSchema(BaseModel):
    phase_id: str
    plan_id: str
    run_id: str
    phase_name: str
    phase_number: int
    steps: list[Any]
    total_steps: int
    completed_steps: int
    failed_steps: int
    status: str
    validation_result: dict[str, Any]
    started_at: str
    completed_at: str
    duration_seconds: float
    rollback_available: bool


class ValidationCheckpointSchema(BaseModel):
    checkpoint_id: str
    plan_id: str
    run_id: str
    phase: str
    phase_number: int
    checks_run: int
    checks_passed: int
    checks_failed: int
    blocking_failures: int
    result: str
    details: list[Any]
    timestamp: str
    duration_seconds: float


class DeploymentPreviewSchema(BaseModel):
    preview_id: str
    plan_id: str
    work_item_id: str
    project: str
    title: str
    summary: str
    affected_files: list[str]
    affected_pages: list[str]
    estimated_changes: int
    risk_level: str
    rollback_strategy: str
    preview_content: dict[str, Any]
    generated_at: str


class DeliveryHealthSchema(BaseModel):
    report_id: str
    project: str
    generated_at: str
    total_plans: int
    total_runs: int
    active_runs: int
    completed_runs: int
    failed_runs: int
    avg_health_score: float
    overall_health: str
    phase_completion_rates: dict[str, float]
    validation_pass_rate: float
    rollback_rate: float
    recovery_count: int
    insights: list[str]
    top_blocked_items: list[str]


class PlansListResponse(BaseModel):
    project: str
    total: int
    plans: list[DeliveryPlanSchema]


class PhasesResponse(BaseModel):
    project: str
    total_phases: int
    phases: list[Any]


class RolloutsResponse(BaseModel):
    total: int
    rollouts: list[Any]
