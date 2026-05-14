from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from .models import ChangeType


class ProjectListResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    projects: list[dict]
    total: int


class ChangesListResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    changes: list[dict]
    total: int
    pending: int
    preview: int


class PreviewsListResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    previews: list[dict]
    total: int
    active: int


class GeneratePRRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    project_id: str
    change_ids: list[str]
    title: str
    description: str
    change_type: ChangeType = ChangeType.feature
    labels: list[str] = []
    reviewers: list[str] = []


class GeneratePRResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    pr_draft: dict
    branch: dict
    preview_workspace: dict
    markdown_body: str
    success: bool
    message: str


class RepoStatusResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    status: str
    projects_tracked: int
    pending_changes: int
    active_previews: int
    open_prs: int
    last_activity: str | None
    safety_mode: bool = True
