from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class OperationType(str, Enum):
    analysis = "analysis"
    proposal = "proposal"
    delivery = "delivery"
    repository = "repository"
    provider_call = "provider_call"
    health_check = "health_check"
    planning = "planning"
    review = "review"


class OperationStatus(str, Enum):
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    rolled_back = "rolled_back"
    skipped = "skipped"
    blocked = "blocked"


class RuntimeMode(str, Enum):
    continuous = "continuous"
    scheduled = "scheduled"
    manual = "manual"
    safe_mode = "safe_mode"
    paused = "paused"


class ScheduleType(str, Enum):
    interval = "interval"
    cron = "cron"
    once = "once"


class RuntimeOperation(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    operation_type: OperationType
    project: str
    status: OperationStatus = OperationStatus.queued
    trust_score: float = 0.5
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result_summary: str = ""
    cost_estimate: float = 0.0
    actual_cost: float = 0.0
    rollback_available: bool = True
    rollback_target: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RuntimeCycle(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    cycle_number: int
    project: str
    mode: RuntimeMode = RuntimeMode.manual
    operations_planned: int = 0
    operations_completed: int = 0
    operations_failed: int = 0
    operations_skipped: int = 0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    status: OperationStatus = OperationStatus.queued
    total_cost: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeSchedule(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project: str
    schedule_type: ScheduleType
    cron_expression: str | None = None
    interval_minutes: int | None = None
    enabled: bool = True
    last_run: datetime | None = None
    next_run: datetime | None = None
    operation_type: OperationType = OperationType.health_check
    max_runs: int | None = None
    run_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RuntimeLimit(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    limit_type: str
    max_value: float
    current_value: float = 0.0
    period: str = "hourly"
    reset_at: datetime | None = None
    exceeded: bool = False
    hard_limit: bool = True


class RuntimeMetric(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    metric_name: str
    value: float
    unit: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    project: str = "all"
    tags: dict[str, str] = Field(default_factory=dict)


class RuntimeFeedback(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    operation_id: str
    feedback_type: str
    score: float
    details: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    applied: bool = False


class RuntimeAnalytics(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    period: str
    total_operations: int = 0
    success_rate: float = 0.0
    avg_duration_seconds: float = 0.0
    total_cost_usd: float = 0.0
    top_projects: list[str] = Field(default_factory=list)
    operations_by_type: dict[str, int] = Field(default_factory=dict)
    operations_by_status: dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
