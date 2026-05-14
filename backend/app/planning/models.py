"""
models.py — Core dataclasses for the Autonomous Execution Planning Layer.

Covers: ExecutionPlan, ExecutionStep, DependencyGraph, Milestone,
RolloutPlan, ValidationSequence, EffortEstimate, DeliveryReport.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Status / phase constants
# ---------------------------------------------------------------------------

STATUS_PENDING     = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED   = "completed"
STATUS_BLOCKED     = "blocked"

PHASE_PREPARATION  = "preparation"
PHASE_IMPLEMENTATION = "implementation"
PHASE_REVIEW       = "review"
PHASE_DEPLOYMENT   = "deployment"
PHASE_VALIDATION   = "validation"

ALL_PHASES = (PHASE_PREPARATION, PHASE_IMPLEMENTATION,
              PHASE_REVIEW, PHASE_DEPLOYMENT, PHASE_VALIDATION)

# Delivery health
DELIVERY_ON_TRACK = "on_track"
DELIVERY_AT_RISK  = "at_risk"
DELIVERY_DELAYED  = "delayed"
DELIVERY_COMPLETED = "completed"

# Validation types
VALIDATION_FUNCTIONAL  = "functional"
VALIDATION_PERFORMANCE = "performance"
VALIDATION_SECURITY    = "security"
VALIDATION_REGRESSION  = "regression"
VALIDATION_UX          = "ux"

# Dependency relationships
REL_REQUIRES  = "requires"
REL_BLOCKS    = "blocks"
REL_ENHANCES  = "enhances"

# Confidence
CONFIDENCE_HIGH   = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW    = "low"


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------------------------
# ExecutionStep — one step inside an ExecutionPlan
# ---------------------------------------------------------------------------

@dataclass
class ExecutionStep:
    step_id: str = field(default_factory=lambda: _uid("step"))
    plan_id: str = ""
    sequence: int = 0
    title: str = ""
    description: str = ""
    phase: str = PHASE_IMPLEMENTATION
    estimated_hours: float = 4.0
    assigned_agent_role: str = ""
    step_dependencies: list[str] = field(default_factory=list)   # other step_ids
    validation_required: bool = False
    status: str = STATUS_PENDING

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# ExecutionPlan — full plan for one WorkItem
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPlan:
    plan_id: str = field(default_factory=lambda: _uid("plan"))
    work_item_id: str = ""
    project: str = ""
    task_type: str = ""
    title: str = ""
    description: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)    # serialised ExecutionSteps
    estimated_days: int = 7
    estimated_hours: float = 0.0
    phases: list[str] = field(default_factory=list)
    priority: str = "medium"
    dependencies: list[str] = field(default_factory=list)        # work_item_ids
    milestone_ids: list[str] = field(default_factory=list)
    validation_required: bool = True
    validation_sequence_id: str = ""
    rollout_plan_id: str = ""
    tags: list[str] = field(default_factory=list)
    source_quarter: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = STATUS_PENDING
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Dependency graph
# ---------------------------------------------------------------------------

@dataclass
class DependencyNode:
    node_id: str = ""            # = work_item_id
    project: str = ""
    title: str = ""
    task_type: str = ""
    priority: str = "medium"
    estimated_days: int = 0
    dependency_layer: int = 0    # 0 = no deps (foundation)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DependencyEdge:
    from_id: str = ""
    to_id: str = ""
    relationship: str = REL_REQUIRES
    critical_path: bool = False
    inferred: bool = False       # True = engine-inferred, False = explicit

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DependencyGraph:
    graph_id: str = field(default_factory=lambda: _uid("dep"))
    project: str = ""
    nodes: list[dict[str, Any]] = field(default_factory=list)
    edges: list[dict[str, Any]] = field(default_factory=list)
    critical_path: list[str] = field(default_factory=list)       # ordered item_ids
    execution_order: list[list[str]] = field(default_factory=list)  # parallel groups
    total_nodes: int = 0
    total_edges: int = 0
    critical_path_length: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Milestone
# ---------------------------------------------------------------------------

@dataclass
class Milestone:
    milestone_id: str = field(default_factory=lambda: _uid("ms"))
    project: str = ""
    quarter: str = ""
    title: str = ""
    description: str = ""
    phase: str = ""
    success_criteria: list[str] = field(default_factory=list)
    work_item_ids: list[str] = field(default_factory=list)
    plan_ids: list[str] = field(default_factory=list)
    deliverables: list[str] = field(default_factory=list)
    estimated_completion_days: int = 0
    estimated_effort_days: int = 0
    priority: str = "high"
    status: str = STATUS_PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Rollout plan
# ---------------------------------------------------------------------------

@dataclass
class ExecutionPhase:
    phase_id: str = field(default_factory=lambda: _uid("ph"))
    rollout_id: str = ""
    phase_number: int = 1
    title: str = ""
    description: str = ""
    work_item_ids: list[str] = field(default_factory=list)
    plan_ids: list[str] = field(default_factory=list)
    start_offset_days: int = 0
    duration_days: int = 14
    exit_criteria: list[str] = field(default_factory=list)
    rollback_trigger: str = ""
    milestone_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RolloutPlan:
    rollout_id: str = field(default_factory=lambda: _uid("ro"))
    project: str = ""
    quarter: str = ""
    title: str = ""
    description: str = ""
    phases: list[dict[str, Any]] = field(default_factory=list)   # serialised ExecutionPhases
    total_duration_days: int = 0
    work_item_ids: list[str] = field(default_factory=list)
    total_work_items: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

@dataclass
class ValidationStep:
    validation_id: str = field(default_factory=lambda: _uid("val"))
    plan_id: str = ""
    step_sequence: int = 0
    title: str = ""
    description: str = ""
    validation_type: str = VALIDATION_FUNCTIONAL
    checks: list[str] = field(default_factory=list)
    pass_criteria: str = ""
    blocking: bool = True
    estimated_hours: float = 2.0
    assigned_role: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ValidationSequence:
    sequence_id: str = field(default_factory=lambda: _uid("vs"))
    plan_id: str = ""
    work_item_id: str = ""
    project: str = ""
    title: str = ""
    steps: list[dict[str, Any]] = field(default_factory=list)
    total_steps: int = 0
    total_blocking_steps: int = 0
    estimated_hours: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Effort estimate
# ---------------------------------------------------------------------------

@dataclass
class EffortEstimate:
    estimate_id: str = field(default_factory=lambda: _uid("est"))
    work_item_id: str = ""
    project: str = ""
    task_type: str = ""
    title: str = ""
    raw_effort_days: int = 0
    complexity_factor: float = 1.0
    risk_buffer_pct: float = 15.0
    adjusted_effort_days: float = 0.0
    risk_buffer_days: float = 0.0
    total_days: float = 0.0
    breakdown: dict[str, float] = field(default_factory=dict)    # phase → days
    confidence: str = CONFIDENCE_MEDIUM
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Delivery tracking
# ---------------------------------------------------------------------------

@dataclass
class DeliveryCheckpoint:
    checkpoint_id: str = field(default_factory=lambda: _uid("cp"))
    plan_id: str = ""
    work_item_id: str = ""
    project: str = ""
    title: str = ""
    target_days_from_start: int = 0
    completion_percentage: float = 0.0
    status: str = DELIVERY_ON_TRACK
    blockers: list[str] = field(default_factory=list)
    notes: str = ""
    priority: str = "medium"
    estimated_days: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class DeliveryReport:
    report_id: str = field(default_factory=lambda: _uid("rep"))
    project: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_plans: int = 0
    on_track: int = 0
    at_risk: int = 0
    delayed: int = 0
    completed: int = 0
    overall_health: str = "good"   # "good" | "caution" | "critical"
    health_score: float = 100.0
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    insights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# PlanningAnalytics — summary returned by /planning/status
# ---------------------------------------------------------------------------

@dataclass
class PlanningAnalytics:
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    total_plans: int = 0
    total_milestones: int = 0
    total_rollouts: int = 0
    total_validation_sequences: int = 0
    total_effort_days: float = 0.0
    avg_steps_per_plan: float = 0.0
    by_project: dict[str, int] = field(default_factory=dict)
    by_task_type: dict[str, int] = field(default_factory=dict)
    by_priority: dict[str, int] = field(default_factory=dict)
    critical_path_items: list[str] = field(default_factory=list)
    top_effort_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
