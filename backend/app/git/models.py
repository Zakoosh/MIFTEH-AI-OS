from pydantic import BaseModel, Field
from typing import Optional


class GitCommandResult(BaseModel):
    command: list[str] = Field(default_factory=list)
    return_code: int = 0
    stdout: str = ""
    stderr: str = ""
    success: bool = True
    error: Optional[str] = None


class RepositoryInfo(BaseModel):
    project_id: str
    name: str = ""
    path: str
    branch: str = ""
    head_sha: str = ""
    protected_branch: bool = False


class GitStatusFile(BaseModel):
    path: str
    status: str
    index_status: str = ""
    worktree_status: str = ""


class GitStatusResult(BaseModel):
    success: bool = True
    project_id: str
    repository: Optional[RepositoryInfo] = None
    branch: str = ""
    is_clean: bool = True
    files: list[GitStatusFile] = Field(default_factory=list)
    raw_status: str = ""
    error: Optional[str] = None


class GitBranchResult(BaseModel):
    success: bool = True
    project_id: str
    branch_name: str
    base_branch: Optional[str] = None
    checked_out: bool = True
    repository: Optional[RepositoryInfo] = None
    error: Optional[str] = None


class GitDiffResult(BaseModel):
    success: bool = True
    project_id: str
    repository: Optional[RepositoryInfo] = None
    staged: bool = False
    base_ref: Optional[str] = None
    has_changes: bool = False
    diff: str = ""
    error: Optional[str] = None


class GitCommitResult(BaseModel):
    success: bool = True
    project_id: str
    repository: Optional[RepositoryInfo] = None
    branch: str = ""
    commit_sha: str = ""
    message: str = ""
    files: list[str] = Field(default_factory=list)
    stage_all: bool = False
    error: Optional[str] = None


class GitPatchFile(BaseModel):
    name: str
    path: str
    project_id: str = ""
    created_at: str = ""
    size_bytes: int = 0


class GitPatchResult(BaseModel):
    success: bool = True
    project_id: str = ""
    repository: Optional[RepositoryInfo] = None
    staged: bool = False
    base_ref: Optional[str] = None
    patch: Optional[GitPatchFile] = None
    patches: list[GitPatchFile] = Field(default_factory=list)
    error: Optional[str] = None
