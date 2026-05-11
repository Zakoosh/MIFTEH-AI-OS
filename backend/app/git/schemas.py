from pydantic import BaseModel, Field
from typing import Optional


class BranchCreateRequest(BaseModel):
    project_id: str = Field(..., description="Workspace project identifier")
    branch_name: str = Field(..., description="New local branch name")
    base_branch: Optional[str] = Field(
        default=None,
        description="Optional local base ref for the new branch",
    )
    checkout: bool = Field(
        default=True,
        description="Checkout the new branch after creation",
    )


class CommitCreateRequest(BaseModel):
    project_id: str = Field(..., description="Workspace project identifier")
    message: str = Field(..., description="Local commit message")
    files: list[str] = Field(
        default_factory=list,
        description="Repository-relative files to stage before committing",
    )
    stage_all: bool = Field(
        default=False,
        description="Stage all repository changes before committing",
    )
