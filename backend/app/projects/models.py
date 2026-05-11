from pydantic import BaseModel, Field
from typing import Optional


class RepositoryInfo(BaseModel):
    git_branch: str = ""
    git_status: str = ""
    last_commit: str = ""
    is_git_repo: bool = False


class ProjectEntry(BaseModel):
    project_id: str
    name: str
    local_path: str = ""
    project_type: str = ""
    available: bool = False
    repository: RepositoryInfo = Field(default_factory=RepositoryInfo)
    linked_agents: list[str] = Field(default_factory=list)
    linked_missions: list[str] = Field(default_factory=list)


class ProjectSummary(BaseModel):
    project_id: str
    name: str
    project_type: str = ""
    available: bool = False
    agents_count: int = 0
    missions_count: int = 0


class WorkspaceManifest(BaseModel):
    workspace_root: str = ""
    projects: list[ProjectEntry] = Field(default_factory=list)


class WorkspaceStatus(BaseModel):
    workspace_root: str = ""
    total_projects: int = 0
    available_projects: int = 0
    unavailable_projects: int = 0
    projects: list[ProjectSummary] = Field(default_factory=list)
