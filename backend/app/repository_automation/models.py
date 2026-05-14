from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field


class ChangeType(str, Enum):
    feature = "feature"
    bugfix = "bugfix"
    refactor = "refactor"
    dependency = "dependency"
    config = "config"
    content = "content"


class ChangeStatus(str, Enum):
    draft = "draft"
    preview = "preview"
    approved = "approved"
    merged = "merged"
    rejected = "rejected"
    rolled_back = "rolled_back"


class BranchStatus(str, Enum):
    active = "active"
    merged = "merged"
    abandoned = "abandoned"
    protected = "protected"


class PRStatus(str, Enum):
    draft = "draft"
    ready = "ready"
    submitted = "submitted"
    merged = "merged"
    closed = "closed"


class PreviewStatus(str, Enum):
    creating = "creating"
    ready = "ready"
    expired = "expired"
    destroyed = "destroyed"


class RepositoryProject(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    repo_url: str
    local_path: str
    default_branch: str = "main"
    status: str = "active"
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RepositoryChange(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    change_type: ChangeType
    files_affected: list[str] = Field(default_factory=list)
    description: str
    status: ChangeStatus = ChangeStatus.draft
    preview_id: str | None = None
    branch_id: str | None = None
    diff_summary: str = ""
    risk_level: str = "low"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BranchRecord(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    branch_name: str
    base_branch: str = "main"
    purpose: str
    status: BranchStatus = BranchStatus.active
    change_ids: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PRDraft(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    branch_id: str
    title: str
    description: str
    changes_summary: str
    files_changed: list[str] = Field(default_factory=list)
    status: PRStatus = PRStatus.draft
    labels: list[str] = Field(default_factory=list)
    reviewers: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class PreviewWorkspace(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    project_id: str
    workspace_path: str
    change_ids: list[str] = Field(default_factory=list)
    status: PreviewStatus = PreviewStatus.creating
    preview_report: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None
    destroyed_at: datetime | None = None


class ChangeAudit(BaseModel):
    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(default_factory=lambda: str(uuid4()))
    action: str
    entity_id: str
    entity_type: str
    details: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    success: bool = True
    error: str | None = None
