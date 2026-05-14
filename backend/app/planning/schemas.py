"""
schemas.py — Pydantic request/response schemas for the Planning Layer API.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class ExecutionStepSchema(BaseModel):
    step_id: str
    plan_id: str
    sequence: int
    title: str
    description: str
    phase: str
    estimated_hours: float
    assigned_agent_role: str
    step_dependencies: list[str]
    validation_required: bool
    status: str


class ExecutionPlanSchema(BaseModel):
    plan_id: str
    work_item_id: str
    project: str
    task_type: str
    title: str
    description: str
    steps: list[Any]
    estimated_days: int
    estimated_hours: float
    phases: list[str]
    priority: str
    dependencies: list[str]
    milestone_ids: list[str]
    validation_required: bool
    validation_sequence_id: str
    rollout_plan_id: str
    tags: list[str]
    source_quarter: str
    created_at: str
    status: str
    metadata: dict[str, Any]


class ExecutionListResponse(BaseModel):
    project: str
    total: int
    plans: list[ExecutionPlanSchema]
    execution_summary: dict[str, Any]


# ---------------------------------------------------------------------------

class DependencyNodeSchema(BaseModel):
    node_id: str
    project: str
    title: str
    task_type: str
    priority: str
    estimated_days: int
    dependency_layer: int


class DependencyEdgeSchema(BaseModel):
    from_id: str
    to_id: str
    relationship: str
    critical_path: bool
    inferred: bool


class DependencyGraphResponse(BaseModel):
    graph_id: str
    project: str
    nodes: list[Any]
    edges: list[Any]
    critical_path: list[str]
    execution_order: list[list[str]]
    total_nodes: int
    total_edges: int
    critical_path_length: int
    created_at: str


class DependenciesResponse(BaseModel):
    project: str
    graph: DependencyGraphResponse


# ---------------------------------------------------------------------------

class MilestoneSchema(BaseModel):
    milestone_id: str
    project: str
    quarter: str
    title: str
    description: str
    phase: str
    success_criteria: list[str]
    work_item_ids: list[str]
    plan_ids: list[str]
    deliverables: list[str]
    estimated_completion_days: int
    estimated_effort_days: int
    priority: str
    status: str
    created_at: str


class MilestonesResponse(BaseModel):
    total: int
    by_quarter: dict[str, list[MilestoneSchema]]
    milestones: list[MilestoneSchema]


# ---------------------------------------------------------------------------

class ExecutionPhaseSchema(BaseModel):
    phase_id: str
    rollout_id: str
    phase_number: int
    title: str
    description: str
    work_item_ids: list[str]
    plan_ids: list[str]
    start_offset_days: int
    duration_days: int
    exit_criteria: list[str]
    rollback_trigger: str
    milestone_ids: list[str]


class RolloutPlanSchema(BaseModel):
    rollout_id: str
    project: str
    quarter: str
    title: str
    description: str
    phases: list[Any]
    total_duration_days: int
    work_item_ids: list[str]
    total_work_items: int
    created_at: str


class RolloutsResponse(BaseModel):
    total: int
    rollouts: list[RolloutPlanSchema]


# ---------------------------------------------------------------------------

class ValidationStepSchema(BaseModel):
    validation_id: str
    plan_id: str
    step_sequence: int
    title: str
    description: str
    validation_type: str
    checks: list[str]
    pass_criteria: str
    blocking: bool
    estimated_hours: float
    assigned_role: str


class ValidationSequenceSchema(BaseModel):
    sequence_id: str
    plan_id: str
    work_item_id: str
    project: str
    title: str
    steps: list[Any]
    total_steps: int
    total_blocking_steps: int
    estimated_hours: float
    created_at: str


# ---------------------------------------------------------------------------

class EffortEstimateSchema(BaseModel):
    estimate_id: str
    work_item_id: str
    project: str
    task_type: str
    title: str
    raw_effort_days: int
    complexity_factor: float
    risk_buffer_pct: float
    adjusted_effort_days: float
    risk_buffer_days: float
    total_days: float
    breakdown: dict[str, float]
    confidence: str
    created_at: str


# ---------------------------------------------------------------------------

class DeliveryCheckpointSchema(BaseModel):
    checkpoint_id: str
    plan_id: str
    work_item_id: str
    project: str
    title: str
    target_days_from_start: int
    completion_percentage: float
    status: str
    blockers: list[str]
    notes: str
    priority: str
    estimated_days: int
    created_at: str


class TrackingResponse(BaseModel):
    project: str
    total_plans: int
    on_track: int
    at_risk: int
    delayed: int
    completed: int
    overall_health: str
    health_score: float
    checkpoints: list[DeliveryCheckpointSchema]
    insights: list[str]
