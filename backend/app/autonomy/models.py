"""
models.py — Core data models for the Autonomous Operational Loops Layer.

All models are plain dataclasses (no ORM). JSON-serializable via to_dict().
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Outcome classification
# ---------------------------------------------------------------------------

OUTCOME_SUCCESS = "success"
OUTCOME_FAILURE = "failure"
OUTCOME_ROLLBACK = "rollback"
OUTCOME_SKIPPED = "skipped"
OUTCOME_DRY_RUN = "dry_run"

CYCLE_RUNNING = "running"
CYCLE_COMPLETED = "completed"
CYCLE_FAILED = "failed"
CYCLE_ABORTED = "aborted"


# ---------------------------------------------------------------------------
# TrustScore
# ---------------------------------------------------------------------------

@dataclass
class TrustScore:
    """
    Per-(project_id, proposal_type) trust score.
    Drives autonomous apply decisions.
    """

    key: str                          # f"{project_id}:{proposal_type}"
    project_id: str
    proposal_type: str
    score: float                      # 0.0 – 100.0
    apply_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    rollback_count: int = 0
    rollback_rate: float = 0.0        # percentage 0–100
    autonomous_apply_allowed: bool = True
    suspended: bool = False
    suspension_reason: str = ""
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TrustScore":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def recompute(self) -> None:
        """Recompute rollback_rate and autonomous_apply_allowed from counters."""
        if self.apply_count > 0:
            self.rollback_rate = round((self.rollback_count / self.apply_count) * 100, 2)
        else:
            self.rollback_rate = 0.0
        self.last_updated = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# OperationOutcome
# ---------------------------------------------------------------------------

@dataclass
class OperationOutcome:
    """Records the outcome of a single autonomous apply operation."""

    outcome_id: str = field(default_factory=lambda: f"out_{uuid.uuid4().hex[:12]}")
    operation_id: str = ""
    proposal_id: str = ""
    project_id: str = ""
    proposal_type: str = ""
    outcome: str = OUTCOME_SUCCESS    # success | failure | rollback | skipped | dry_run
    simulated: bool = False
    dry_run: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OperationOutcome":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# AutonomyCycle
# ---------------------------------------------------------------------------

@dataclass
class AutonomyCycle:
    """
    Represents one complete autonomous operational cycle.
    A cycle selects, validates, applies, and tracks outcomes for N proposals.
    """

    cycle_id: str = field(default_factory=lambda: f"cycle_{uuid.uuid4().hex[:12]}")
    triggered_by: str = "manual"      # "manual" | "scheduler" | "api"
    dry_run: bool = False
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""
    proposals_evaluated: int = 0
    proposals_selected: int = 0
    proposals_applied: int = 0
    proposals_skipped: int = 0
    outcome_ids: list[str] = field(default_factory=list)
    trust_updates: dict[str, Any] = field(default_factory=dict)
    status: str = CYCLE_RUNNING
    error: str = ""
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AutonomyCycle":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def complete(self, status: str = CYCLE_COMPLETED, error: str = "") -> None:
        self.status = status
        self.error = error
        self.completed_at = datetime.now().isoformat()
        self.summary = (
            f"Evaluated {self.proposals_evaluated}, selected {self.proposals_selected}, "
            f"applied {self.proposals_applied}, skipped {self.proposals_skipped}."
        )


# ---------------------------------------------------------------------------
# FeedbackEntry
# ---------------------------------------------------------------------------

@dataclass
class FeedbackEntry:
    """Immutable record of a trust adjustment made by the feedback loop."""

    feedback_id: str = field(default_factory=lambda: f"fb_{uuid.uuid4().hex[:12]}")
    cycle_id: str = ""
    proposal_id: str = ""
    proposal_type: str = ""
    project_id: str = ""
    insight: str = ""
    action_taken: str = ""            # "trust_increased" | "trust_decreased" | "suspended" | "reinstated"
    old_score: float = 0.0
    new_score: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "FeedbackEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# RiskGateResult
# ---------------------------------------------------------------------------

@dataclass
class RiskGateResult:
    """Result of risk controller evaluation for a single proposal."""

    proposal_id: str
    proposal_type: str
    project_id: str
    allowed: bool
    trust_score: float
    rollback_rate: float
    reasons_blocked: list[str] = field(default_factory=list)
    reasons_allowed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# AutonomyConfig
# ---------------------------------------------------------------------------

@dataclass
class AutonomyConfig:
    """
    Runtime configuration for the autonomy engine.
    Persisted to app/memory/autonomy/config/config.json.
    """

    enabled: bool = True                    # Master kill switch
    dry_run_mode: bool = False              # Global dry-run override
    trust_threshold: float = 75.0          # Min trust score to auto-apply
    rollback_threshold: float = 20.0       # Max rollback rate (%) before suspension
    max_per_cycle: int = 3                  # Max proposals applied per cycle
    max_per_day: int = 10                   # Max proposals applied per day
    trust_gain_on_success: float = 2.0     # Trust points gained on success
    trust_loss_on_failure: float = 10.0    # Trust points lost on failure/rollback
    initial_trust_score: float = 80.0      # Starting trust for new proposal types
    suspension_threshold: int = 3          # Consecutive failures before suspension
    reinstate_threshold: float = 60.0      # Trust score needed for reinstatement

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AutonomyConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def new_cycle_id() -> str:
    return f"cycle_{uuid.uuid4().hex[:12]}"


def now_iso() -> str:
    return datetime.now().isoformat()
