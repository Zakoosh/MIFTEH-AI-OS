"""
models.py — Core data models for the Safe Autonomous Apply Layer.

All models are plain dataclasses (no ORM). Serialization helpers
produce plain dicts compatible with JSON file storage.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Risk classification
# ---------------------------------------------------------------------------

RISK_LEVELS = ("low", "medium", "high")

LOW_RISK = "low"
MEDIUM_RISK = "medium"
HIGH_RISK = "high"


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------

@dataclass
class Proposal:
    """A structured improvement proposal waiting to be applied."""

    id: str
    project_id: str                  # "yallaplays" | "fionera"
    proposal_type: str               # "seo" | "metadata" | "dashboard" | "manifest" | "landing_page" | "category" | "widget" | "watchlist"
    title: str
    description: str
    target_file: str                 # Relative path within the project
    changes: dict[str, Any]          # Structured change specification
    risk_level: str = LOW_RISK       # Only low-risk proposals are auto-applied
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"          # "pending" | "validated" | "applied" | "rolled_back" | "rejected"
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Proposal":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ValidationResult:
    """Outcome of pre-apply validation."""

    proposal_id: str
    valid: bool
    risk_level: str
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PreviewResult:
    """Human-readable preview of what the apply will do."""

    proposal_id: str
    operation_type: str
    target_file: str
    before_summary: str
    after_summary: str
    changes_count: int
    simulated: bool = False          # True when target path does not exist on disk
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Patch:
    """Represents a generated patch ready for application."""

    operation_id: str
    proposal_id: str
    target_file: str
    original_content: str
    patched_content: str
    diff_lines: list[str] = field(default_factory=list)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ApplyResult:
    """Final result returned after executing the full apply pipeline."""

    proposal_id: str
    operation_id: str
    project: str
    validated: bool
    preview_generated: bool
    patch_generated: bool
    applied: bool
    rollback_available: bool
    simulated: bool = False
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class RollbackRecord:
    """Tracks a backup so an applied change can be reversed."""

    operation_id: str
    proposal_id: str
    target_file: str
    backup_content: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    restored: bool = False
    restored_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class AuditEntry:
    """Immutable audit trail record for every apply action."""

    audit_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    operation_id: str = ""
    proposal_id: str = ""
    project_id: str = ""
    action: str = ""                 # "validate" | "preview" | "patch" | "apply" | "rollback" | "reject"
    status: str = ""                 # "success" | "failure" | "skipped"
    actor: str = "mifteh-apply-engine"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def new_operation_id() -> str:
    """Generate a unique operation ID."""
    return f"op_{uuid.uuid4().hex[:12]}"
