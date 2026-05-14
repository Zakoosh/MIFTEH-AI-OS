"""
models.py — Core data models for the Multi-Agent Collaborative Execution Layer.

All models are plain dataclasses (no ORM). JSON-serializable via to_dict().

Role separation is enforced structurally:
  Implementers  → execute the task (write code / content / analysis)
  Reviewers     → review implementer work (must be different agents)
  Validators    → independent verification (must differ from both)
  Orchestrators → coordinate the session (one optional per session)
  QA            → quality assurance checks
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Role constants
# ---------------------------------------------------------------------------

ROLE_IMPLEMENTER  = "implementer"
ROLE_REVIEWER     = "reviewer"
ROLE_VALIDATOR    = "validator"
ROLE_ORCHESTRATOR = "orchestrator"
ROLE_QA           = "qa"

ALL_ROLES = (ROLE_IMPLEMENTER, ROLE_REVIEWER, ROLE_VALIDATOR, ROLE_ORCHESTRATOR, ROLE_QA)


# ---------------------------------------------------------------------------
# Thread / session states
# ---------------------------------------------------------------------------

THREAD_PENDING    = "pending"
THREAD_RUNNING    = "running"
THREAD_REVIEW     = "review"
THREAD_CONSENSUS  = "consensus"
THREAD_APPROVED   = "approved"
THREAD_REJECTED   = "rejected"
THREAD_CONFLICT   = "conflict"
THREAD_COMPLETED  = "completed"

SESSION_RUNNING   = "running"
SESSION_APPROVED  = "approved"
SESSION_REJECTED  = "rejected"
SESSION_CONFLICT  = "conflict"
SESSION_COMPLETED = "completed"


# ---------------------------------------------------------------------------
# AgentRole
# ---------------------------------------------------------------------------

@dataclass
class AgentRole:
    """Describes the role and capabilities of one agent in a session."""

    agent_name: str
    role: str                           # one of ALL_ROLES
    division: str                       # marketing | engineering | testing | …
    specialty: str                      # seo-specialist | code-reviewer | …
    capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentRole":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# AgentContribution
# ---------------------------------------------------------------------------

@dataclass
class AgentContribution:
    """The output produced by one agent during its execution phase."""

    contribution_id: str = field(default_factory=lambda: f"ctr_{uuid.uuid4().hex[:12]}")
    thread_id: str = ""
    session_id: str = ""
    agent_name: str = ""
    role: str = ROLE_IMPLEMENTER
    task: str = ""
    output: str = ""
    score: float = 0.0                  # self-assessed confidence (implementers)
    confidence: float = 0.0            # 0–100
    simulated: bool = True             # True when no LLM call was made
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AgentContribution":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# ReviewRecord
# ---------------------------------------------------------------------------

@dataclass
class ReviewRecord:
    """A single agent's review of another agent's contribution."""

    review_id: str = field(default_factory=lambda: f"rev_{uuid.uuid4().hex[:12]}")
    thread_id: str = ""
    session_id: str = ""
    reviewer_agent: str = ""           # must be a REVIEWER or VALIDATOR
    reviewed_agent: str = ""           # the IMPLEMENTER being reviewed
    contribution_id: str = ""
    score: float = 0.0                 # 0–100
    approved: bool = False
    feedback: str = ""
    concerns: list[str] = field(default_factory=list)
    role: str = ROLE_REVIEWER
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# ConsensusScore
# ---------------------------------------------------------------------------

@dataclass
class ConsensusScore:
    """Aggregated consensus across all reviewers and validators."""

    consensus_id: str = field(default_factory=lambda: f"con_{uuid.uuid4().hex[:12]}")
    session_id: str = ""
    thread_id: str = ""
    individual_scores: dict[str, float] = field(default_factory=dict)   # agent → score
    role_weights: dict[str, float] = field(default_factory=dict)        # agent → weight
    weighted_score: float = 0.0
    consensus_score: float = 0.0
    approved: bool = False
    threshold: float = 75.0
    abstentions: list[str] = field(default_factory=list)
    score_spread: float = 0.0          # max - min (divergence indicator)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConsensusScore":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# ReviewChain
# ---------------------------------------------------------------------------

@dataclass
class ReviewChain:
    """Ordered sequence of reviews for one execution thread."""

    chain_id: str = field(default_factory=lambda: f"chain_{uuid.uuid4().hex[:12]}")
    thread_id: str = ""
    session_id: str = ""
    review_ids: list[str] = field(default_factory=list)
    reviewers: list[str] = field(default_factory=list)
    validators: list[str] = field(default_factory=list)
    chain_approved: bool = False
    completed: bool = False
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewChain":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# QualityReport
# ---------------------------------------------------------------------------

@dataclass
class QualityReport:
    """Output of the quality control pass over a completed thread."""

    report_id: str = field(default_factory=lambda: f"qc_{uuid.uuid4().hex[:12]}")
    thread_id: str = ""
    session_id: str = ""
    checks_passed: list[str] = field(default_factory=list)
    checks_failed: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    approved: bool = False
    recommendations: list[str] = field(default_factory=list)
    reviewer_coverage: float = 0.0    # % of implementers reviewed
    validator_independence: bool = True
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "QualityReport":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# ConflictRecord
# ---------------------------------------------------------------------------

@dataclass
class ConflictRecord:
    """A detected conflict between agents in a collaboration session."""

    conflict_id: str = field(default_factory=lambda: f"cfl_{uuid.uuid4().hex[:12]}")
    thread_id: str = ""
    session_id: str = ""
    conflicting_agents: list[str] = field(default_factory=list)
    conflict_type: str = ""            # "score_divergence" | "role_violation" | "contradictory_output"
    description: str = ""
    resolution: str = ""              # "majority_vote" | "escalation" | "abstention" | "override"
    resolved: bool = False
    resolved_by: str = ""             # agent name or "system"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConflictRecord":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# ExecutionThread
# ---------------------------------------------------------------------------

@dataclass
class ExecutionThread:
    """
    One collaborative execution unit.

    A thread contains all agents executing on a single task/proposal,
    their contributions, the review chain, and the consensus outcome.
    """

    thread_id: str = field(default_factory=lambda: f"thr_{uuid.uuid4().hex[:12]}")
    session_id: str = ""
    mission: str = ""
    proposal_id: str = ""
    project_id: str = ""
    agents: list[str] = field(default_factory=list)
    agent_roles: dict[str, str] = field(default_factory=dict)  # agent → role
    implementers: list[str] = field(default_factory=list)
    reviewers: list[str] = field(default_factory=list)
    validators: list[str] = field(default_factory=list)
    status: str = THREAD_PENDING
    contribution_ids: list[str] = field(default_factory=list)
    review_ids: list[str] = field(default_factory=list)
    chain_id: str = ""
    consensus_score: float = 0.0
    quality_score: float = 0.0
    approved: bool = False
    conflicts: int = 0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionThread":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def complete(self, approved: bool, error: str = "") -> None:
        self.approved = approved
        self.status = THREAD_APPROVED if approved else THREAD_REJECTED
        self.completed_at = datetime.now().isoformat()
        self.error = error


# ---------------------------------------------------------------------------
# CollaborationSession
# ---------------------------------------------------------------------------

@dataclass
class CollaborationSession:
    """
    Top-level container for a multi-agent collaboration.

    May contain one or more ExecutionThreads (one per task/proposal).
    """

    session_id: str = field(default_factory=lambda: f"sess_{uuid.uuid4().hex[:12]}")
    mission: str = ""
    proposal_id: str = ""
    project_id: str = ""
    triggered_by: str = "api"
    thread_ids: list[str] = field(default_factory=list)
    agents: list[str] = field(default_factory=list)
    agent_roles: dict[str, str] = field(default_factory=dict)
    consensus_score: float = 0.0
    approved: bool = False
    review_status: str = "pending"     # pending | approved | rejected | conflict
    reviewed_by: list[str] = field(default_factory=list)
    quality_score: float = 0.0
    conflicts_detected: int = 0
    conflicts_resolved: int = 0
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""
    status: str = SESSION_RUNNING
    summary: str = ""
    insights: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CollaborationSession":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def complete(self, approved: bool) -> None:
        self.approved = approved
        self.review_status = "approved" if approved else "rejected"
        self.status = SESSION_APPROVED if approved else SESSION_REJECTED
        self.completed_at = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now().isoformat()
