from typing import Optional

from fastapi import APIRouter, Query

from app.git.branch_manager import create_branch
from app.git.commit_manager import create_commit
from app.git.diff_manager import generate_diff
from app.git.patch_manager import generate_patch_file, list_patch_files
from app.git.schemas import BranchCreateRequest, CommitCreateRequest
from app.git.status_manager import get_repository_status


router = APIRouter(prefix="/git", tags=["git"])


@router.get("/status/{project_id}")
def repository_status(project_id: str):
    return get_repository_status(project_id).model_dump()


@router.post("/branch/create")
def create_repository_branch(request: BranchCreateRequest):
    return create_branch(
        project_id=request.project_id,
        branch_name=request.branch_name,
        base_branch=request.base_branch,
        checkout=request.checkout,
    ).model_dump()


@router.get("/diff/{project_id}")
def repository_diff(
    project_id: str,
    staged: bool = Query(default=False),
    base_ref: Optional[str] = Query(default=None),
):
    return generate_diff(
        project_id=project_id,
        staged=staged,
        base_ref=base_ref,
    ).model_dump()


@router.post("/commit")
def create_repository_commit(request: CommitCreateRequest):
    return create_commit(
        project_id=request.project_id,
        message=request.message,
        files=request.files,
        stage_all=request.stage_all,
    ).model_dump()


@router.get("/patches")
def repository_patches(
    project_id: Optional[str] = Query(default=None),
    staged: bool = Query(default=False),
    base_ref: Optional[str] = Query(default=None),
):
    if project_id:
        return generate_patch_file(
            project_id=project_id,
            staged=staged,
            base_ref=base_ref,
        ).model_dump()

    return {"success": True, "patches": [patch.model_dump() for patch in list_patch_files()]}
