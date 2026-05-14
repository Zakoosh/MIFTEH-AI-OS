from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class DeploymentStatus(str, Enum):
    pending = "pending"
    building = "building"
    staging = "staging"
    awaiting_approval = "awaiting_approval"
    deploying = "deploying"
    deployed = "deployed"
    failed = "failed"
    rolled_back = "rolled_back"
    cancelled = "cancelled"


class Environment(str, Enum):
    development = "development"
    staging = "staging"
    production = "production"


class RolloutStrategy(str, Enum):
    blue_green = "blue_green"
    canary = "canary"
    rolling = "rolling"
    direct = "direct"


class PipelineStatus(str, Enum):
    queued = "queued"
    running = "running"
    passed = "passed"
    failed = "failed"
    cancelled = "cancelled"


class ReleaseStatus(str, Enum):
    draft = "draft"
    released = "released"
    deprecated = "deprecated"


class Deployment(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    environment: Environment
    version: str
    strategy: RolloutStrategy = RolloutStrategy.blue_green
    status: DeploymentStatus = DeploymentStatus.pending
    triggered_by: str = "manual"
    approval_required: bool = True
    approved_by: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    rollback_target: str | None = None
    preview_url: str | None = None
    health_check_url: str | None = None
    notes: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class StagingDeployment(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    branch: str
    version: str
    preview_url: str | None = None
    status: DeploymentStatus = DeploymentStatus.staging
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    destroyed_at: datetime | None = None


class PipelineStage(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    pipeline_id: str
    name: str
    order: int
    status: PipelineStatus = PipelineStatus.queued
    duration_seconds: float | None = None
    logs_path: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class CICDPipeline(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    pipeline_name: str
    stages: list[str] = Field(default_factory=list)
    status: PipelineStatus = PipelineStatus.queued
    triggered_by: str = "push"
    branch: str = "main"
    commit_sha: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class Release(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    version: str
    tag: str
    changelog: str = ""
    deployed_envs: list[str] = Field(default_factory=list)
    status: ReleaseStatus = ReleaseStatus.draft
    created_at: datetime = Field(default_factory=datetime.utcnow)
    released_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeploymentHealth(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    project_id: str
    environment: str
    status: str = "unknown"
    last_deployment: datetime | None = None
    uptime_pct: float = 100.0
    error_rate: float = 0.0
    checks_passed: int = 0
    checks_failed: int = 0
    checked_at: datetime = Field(default_factory=datetime.utcnow)


class RollbackRecord(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    deployment_id: str
    reason: str
    target_version: str
    status: str = "initiated"
    initiated_by: str = "system"
    initiated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    success: bool | None = None
    error: str | None = None
