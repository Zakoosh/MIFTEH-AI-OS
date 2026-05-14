from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class OperationProject(str, Enum):
    yallaplays = "yallaplays"
    fionera = "fionera"


class OutputType(str, Enum):
    seo_page = "seo_page"
    category_page = "category_page"
    metadata_patch = "metadata_patch"
    mobile_optimization = "mobile_optimization"
    internal_linking = "internal_linking"
    game_recommendation = "game_recommendation"
    finance_widget = "finance_widget"
    market_insight = "market_insight"
    watchlist_improvement = "watchlist_improvement"
    analytics_dashboard = "analytics_dashboard"
    ux_proposal = "ux_proposal"
    content_patch = "content_patch"


class OutputStatus(str, Enum):
    generated = "generated"
    previewed = "previewed"
    approved = "approved"
    applied = "applied"
    rejected = "rejected"
    rolled_back = "rolled_back"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class OperationalOutput(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project: OperationProject
    output_type: OutputType
    title: str
    description: str
    content: dict[str, Any] = Field(default_factory=dict)
    patch_files: list[dict[str, Any]] = Field(default_factory=list)
    status: OutputStatus = OutputStatus.generated
    risk_level: RiskLevel = RiskLevel.low
    preview_id: str | None = None
    apply_id: str | None = None
    rollback_available: bool = True
    ai_generated: bool = False
    provider_used: str = "template"
    tokens_used: int = 0
    cost_usd: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationalPreview(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    output_id: str
    project: OperationProject
    preview_html: str = ""
    preview_markdown: str = ""
    diff_summary: str = ""
    files_changed: list[str] = Field(default_factory=list)
    estimated_impact: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class OperationBatch(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project: OperationProject
    output_type: OutputType
    outputs: list[str] = Field(default_factory=list)
    total_generated: int = 0
    total_applied: int = 0
    status: str = "completed"
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class OperationalAnalytics(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    project: str
    period: str
    total_outputs: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)
    applied_count: int = 0
    pending_count: int = 0
    total_cost_usd: float = 0.0
    ai_generated_count: int = 0
    generated_at: datetime = Field(default_factory=datetime.utcnow)
