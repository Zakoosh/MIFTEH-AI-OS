"""
models.py — Core dataclasses for the Autonomous Delivery Execution Layer.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Status / result constants
# ---------------------------------------------------------------------------

DELIVERY_PENDING     = "pending"
DELIVERY_RUNNING     = "running"
DELIVERY_COMPLETED   = "completed"
DELIVERY_FAILED      = "failed"
DELIVERY_ROLLED_BACK = "rolled_back"
DELIVERY_BLOCKED     = "blocked"

PHASE_PENDING    = "pending"
PHASE_RUNNING    = "running"
PHASE_COMPLETED  = "completed"
PHASE_FAILED     = "failed"
PHASE_SKIPPED    = "skipped"

VALIDATION_PASSED  = "passed"
VALIDATION_FAILED  = "failed"
VALIDATION_SKIPPED = "skipped"

RECOVERY_ROLLBACK  = "rollback"
RECOVERY_RETRY     = "retry"
RECOVERY_SKIP      = "skip"
RECOVERY_ESCALATE  = "escalate"

HEALTH_GOOD     = "good"
HEALTH_CAUTION  = "caution"
HEALTH_CRITICAL = "critical"

# Canonical phase execution order
PHASE_ORDER = ["preparation", "implementation", "review", "deployment", "validation"]


# ---------------------------------------------------------------------------
# Simulation helpers (deterministic — same seed → same result)
# ---------------------------------------------------------------------------

def _sim_success(seed: str, rate: float = 0.96) -> bool:
    h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
    return (h % 100) < int(rate * 100)


def _sim_score(seed: str, base: float = 87.0, spread: float = 13.0) -> float:
    h = int(hashlib.sha256(seed.encode()).hexdigest(), 16)
    offset = (h % 1000) / 1000.0 * spread
    return round(min(100.0, base + offset), 1)


def _now() -> str:
    return datetime.now().isoformat()


def _uid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


# ---------------------------------------------------------------------------
# DeliveryStep — one executed step in a phase
# ---------------------------------------------------------------------------

@dataclass
class DeliveryStep:
    step_id: str = ""
    plan_id: str = ""
    run_id: str = ""
    sequence: int = 0
    title: str = ""
    phase: str = ""
    estimated_hours: float = 4.0
    actual_hours: float = 4.0
    assigned_agent_role: str = ""
    status: str = PHASE_COMPLETED
    validation_required: bool = False
    output: str = ""
    error: str = ""
    simulated: bool = True
    executed_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# ValidationCheckpoint — gate between phases
# ---------------------------------------------------------------------------

@dataclass
class ValidationCheckpoint:
    checkpoint_id: str = field(default_factory=lambda: _uid("ck"))
    plan_id: str = ""
    run_id: str = ""
    phase: str = ""
    phase_number: int = 0
    checks_run: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    blocking_failures: int = 0
    result: str = VALIDATION_PASSED
    details: list[dict[str, Any]] = field(default_factory=list)
    timestamp: str = field(default_factory=_now)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# DeliveryPhase — execution record for one phase
# ---------------------------------------------------------------------------

@dataclass
class DeliveryPhase:
    phase_id: str = field(default_factory=lambda: _uid("ph"))
    plan_id: str = ""
    run_id: str = ""
    phase_name: str = ""
    phase_number: int = 0
    steps: list[dict[str, Any]] = field(default_factory=list)
    total_steps: int = 0
    completed_steps: int = 0
    failed_steps: int = 0
    status: str = PHASE_COMPLETED
    validation_result: dict[str, Any] = field(default_factory=dict)
    started_at: str = field(default_factory=_now)
    completed_at: str = field(default_factory=_now)
    duration_seconds: float = 0.0
    rollback_available: bool = True

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# DeploymentPreview — what will change before it changes
# ---------------------------------------------------------------------------

@dataclass
class DeploymentPreview:
    preview_id: str = field(default_factory=lambda: _uid("pr"))
    plan_id: str = ""
    work_item_id: str = ""
    project: str = ""
    title: str = ""
    summary: str = ""
    affected_files: list[str] = field(default_factory=list)
    affected_pages: list[str] = field(default_factory=list)
    estimated_changes: int = 0
    risk_level: str = "low"
    rollback_strategy: str = ""
    preview_content: dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# RecoveryRecord — what happened when a phase failed
# ---------------------------------------------------------------------------

@dataclass
class RecoveryRecord:
    recovery_id: str = field(default_factory=lambda: _uid("rec"))
    plan_id: str = ""
    run_id: str = ""
    phase: str = ""
    trigger: str = ""
    action: str = RECOVERY_RETRY
    action_details: str = ""
    success: bool = True
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# CollaborativeDeliverySession
# ---------------------------------------------------------------------------

@dataclass
class CollaborativeDeliverySession:
    session_id: str = field(default_factory=lambda: _uid("cds"))
    plan_id: str = ""
    work_item_id: str = ""
    project: str = ""
    mission: str = ""
    agents_assigned: list[str] = field(default_factory=list)
    roles: dict[str, str] = field(default_factory=dict)
    contributions: list[dict[str, Any]] = field(default_factory=list)
    review_status: str = "approved"
    consensus_score: float = 88.0
    approved: bool = True
    created_at: str = field(default_factory=_now)
    completed_at: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# DeliveryAuditEntry
# ---------------------------------------------------------------------------

@dataclass
class DeliveryAuditEntry:
    audit_id: str = field(default_factory=lambda: _uid("aud"))
    plan_id: str = ""
    run_id: str = ""
    action: str = ""
    actor: str = "delivery-engine"
    status: str = DELIVERY_COMPLETED
    phase: str = ""
    details: str = ""
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# DeliveryRun — full execution record
# ---------------------------------------------------------------------------

@dataclass
class DeliveryRun:
    run_id: str = field(default_factory=lambda: _uid("run"))
    plan_id: str = ""
    work_item_id: str = ""
    project: str = ""
    title: str = ""
    triggered_by: str = "autonomous"
    dry_run: bool = True
    simulated: bool = True
    current_phase: str = ""
    phases_completed: list[str] = field(default_factory=list)
    phases_remaining: list[str] = field(default_factory=list)
    completed_steps: int = 0
    total_steps: int = 0
    remaining_steps: int = 0
    health_score: float = 100.0
    validation_passed: bool = True
    rollback_ready: bool = True
    deployment_preview_generated: bool = False
    recovery_actions: list[dict[str, Any]] = field(default_factory=list)
    phases: list[dict[str, Any]] = field(default_factory=list)
    checkpoints: list[dict[str, Any]] = field(default_factory=list)
    collaborative_session_id: str = ""
    started_at: str = field(default_factory=_now)
    completed_at: str = field(default_factory=_now)
    status: str = DELIVERY_COMPLETED
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# DeliveryPlan — lifecycle wrapper around a planning-layer ExecutionPlan
# ---------------------------------------------------------------------------

@dataclass
class DeliveryPlan:
    plan_id: str = ""
    work_item_id: str = ""
    project: str = ""
    title: str = ""
    description: str = ""
    task_type: str = ""
    priority: str = "medium"
    phases: list[str] = field(default_factory=list)
    total_steps: int = 0
    total_estimated_hours: float = 0.0
    validation_required: bool = True
    rollback_available: bool = True
    dependencies: list[str] = field(default_factory=list)
    source_quarter: str = ""
    latest_run_id: str = ""
    total_runs: int = 0
    created_at: str = field(default_factory=_now)
    status: str = DELIVERY_PENDING

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# DeliveryHealthReport
# ---------------------------------------------------------------------------

@dataclass
class DeliveryHealthReport:
    report_id: str = field(default_factory=lambda: _uid("hr"))
    project: str = "all"
    generated_at: str = field(default_factory=_now)
    total_plans: int = 0
    total_runs: int = 0
    active_runs: int = 0
    completed_runs: int = 0
    failed_runs: int = 0
    avg_health_score: float = 0.0
    overall_health: str = HEALTH_GOOD
    phase_completion_rates: dict[str, float] = field(default_factory=dict)
    validation_pass_rate: float = 0.0
    rollback_rate: float = 0.0
    recovery_count: int = 0
    insights: list[str] = field(default_factory=list)
    top_blocked_items: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
