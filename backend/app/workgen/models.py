"""
models.py — Core data models for the Real Autonomous Work Generation Layer.

Work items represent structured, actionable tasks generated autonomously
for YallaPlays and Fionera. All models are plain dataclasses.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Task type constants
# ---------------------------------------------------------------------------

TASK_SEO_CAMPAIGN    = "seo_campaign"
TASK_FEATURE         = "feature"
TASK_IMPLEMENTATION  = "implementation"
TASK_ROADMAP         = "roadmap"
TASK_UX              = "ux"
TASK_DASHBOARD       = "dashboard"
TASK_MONETIZATION    = "monetization"
TASK_CAMPAIGN        = "campaign"
TASK_OPTIMIZATION    = "optimization"
TASK_CONTENT         = "content"
TASK_WATCHLIST       = "watchlist"
TASK_WIDGET          = "widget"
TASK_ANALYTICS       = "analytics"

ALL_TASK_TYPES = (
    TASK_SEO_CAMPAIGN, TASK_FEATURE, TASK_IMPLEMENTATION, TASK_ROADMAP,
    TASK_UX, TASK_DASHBOARD, TASK_MONETIZATION, TASK_CAMPAIGN,
    TASK_OPTIMIZATION, TASK_CONTENT, TASK_WATCHLIST, TASK_WIDGET, TASK_ANALYTICS,
)

# Priority levels
PRIORITY_CRITICAL = "critical"
PRIORITY_HIGH     = "high"
PRIORITY_MEDIUM   = "medium"
PRIORITY_LOW      = "low"

# Effort levels
EFFORT_LOW    = "low"       # 1–5 days
EFFORT_MEDIUM = "medium"    # 5–15 days
EFFORT_HIGH   = "high"      # 15+ days

# Status
STATUS_PENDING     = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED   = "completed"
STATUS_BLOCKED     = "blocked"


# ---------------------------------------------------------------------------
# WorkItem
# ---------------------------------------------------------------------------

@dataclass
class WorkItem:
    """
    A single structured, actionable work item ready for execution.

    Work items are generated autonomously and can be fed directly into
    the Collaboration Layer (as missions) or the Apply Layer (as proposals).
    """

    item_id: str = field(default_factory=lambda: f"wi_{uuid.uuid4().hex[:12]}")
    project: str = ""                          # "yallaplays" | "fionera"
    task_type: str = TASK_FEATURE              # one of ALL_TASK_TYPES
    title: str = ""
    description: str = ""
    priority: str = PRIORITY_MEDIUM
    estimated_impact: float = 70.0             # 0–100 business impact score
    estimated_effort: str = EFFORT_MEDIUM
    estimated_days: int = 7
    recommended_agents: list[str] = field(default_factory=list)
    collaboration_mission: str = ""            # maps to a Collaboration mission
    apply_proposal_type: str = ""              # maps to an Apply Layer proposal type
    tags: list[str] = field(default_factory=list)
    status: str = STATUS_PENDING
    source: str = "workgen"                    # generator that created this
    quarter: str = ""                          # e.g. "Q3-2026"
    roi_estimate: str = ""                     # qualitative ROI description
    dependencies: list[str] = field(default_factory=list)  # other item_ids
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkItem":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Campaign
# ---------------------------------------------------------------------------

@dataclass
class Campaign:
    """A structured SEO or marketing campaign with target keywords and pages."""

    campaign_id: str = field(default_factory=lambda: f"cam_{uuid.uuid4().hex[:12]}")
    project: str = ""
    campaign_type: str = "seo"                 # seo | growth | content | app_store
    title: str = ""
    description: str = ""
    target_keywords: list[str] = field(default_factory=list)
    target_pages: list[str] = field(default_factory=list)
    estimated_impact: float = 80.0
    estimated_effort: str = EFFORT_MEDIUM
    timeline_weeks: int = 6
    recommended_agents: list[str] = field(default_factory=list)
    work_item_ids: list[str] = field(default_factory=list)
    monthly_search_volume: int = 0             # estimated total monthly searches
    difficulty_score: float = 50.0             # keyword difficulty 0–100
    priority: str = PRIORITY_HIGH
    status: str = STATUS_PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Campaign":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# RoadmapItem
# ---------------------------------------------------------------------------

@dataclass
class RoadmapItem:
    """A strategic roadmap entry spanning multiple work items."""

    roadmap_id: str = field(default_factory=lambda: f"rm_{uuid.uuid4().hex[:12]}")
    project: str = ""
    quarter: str = ""                          # "Q2-2026" | "Q3-2026" | "Q4-2026"
    title: str = ""
    description: str = ""
    theme: str = ""                            # strategic theme for this quarter
    work_item_ids: list[str] = field(default_factory=list)
    total_estimated_days: int = 0
    expected_outcomes: list[str] = field(default_factory=list)
    success_metrics: list[str] = field(default_factory=list)
    priority: str = PRIORITY_HIGH
    status: str = STATUS_PENDING
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RoadmapItem":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# WorkBatch
# ---------------------------------------------------------------------------

@dataclass
class WorkBatch:
    """
    A cohesive batch of work items scoped to a project and generation run.
    Used to group related work items for handoff to the Collaboration Layer.
    """

    batch_id: str = field(default_factory=lambda: f"bat_{uuid.uuid4().hex[:12]}")
    project: str = ""
    batch_type: str = ""                       # "seo" | "features" | "roadmap" | "full"
    title: str = ""
    work_item_ids: list[str] = field(default_factory=list)
    campaign_ids: list[str] = field(default_factory=list)
    roadmap_ids: list[str] = field(default_factory=list)
    total_items: int = 0
    total_estimated_days: int = 0
    avg_estimated_impact: float = 0.0
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    summary: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkBatch":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# PriorityScore
# ---------------------------------------------------------------------------

@dataclass
class PriorityScore:
    """
    Computed priority score for one work item.
    Combines impact, feasibility, urgency, and strategic alignment.
    """

    item_id: str = ""
    title: str = ""
    project: str = ""
    task_type: str = ""
    composite_score: float = 0.0               # 0–100 final score
    impact_score: float = 0.0
    feasibility_score: float = 0.0
    urgency_score: float = 0.0
    alignment_score: float = 0.0
    priority: str = PRIORITY_MEDIUM
    rank: int = 0
    computed_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# WorkGenConfig
# ---------------------------------------------------------------------------

@dataclass
class WorkGenConfig:
    """Runtime configuration for the work generation engine."""

    yallaplays_enabled: bool = True
    fionera_enabled: bool = True
    max_items_per_batch: int = 20
    include_seo_campaigns: bool = True
    include_features: bool = True
    include_implementation: bool = True
    include_roadmap: bool = True
    include_ux: bool = True
    include_monetization: bool = True
    priority_threshold: str = PRIORITY_LOW     # minimum priority to include
    default_quarter: str = "Q3-2026"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "WorkGenConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now().isoformat()
