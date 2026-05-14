from __future__ import annotations
from fastapi import APIRouter, HTTPException, Query
from ..repository_automation.repository_engine import RepositoryEngine
from ..repository_automation.schemas import GeneratePRRequest, GeneratePRResponse, RepoStatusResponse

router = APIRouter(prefix="/repo", tags=["repository_automation"])
engine = RepositoryEngine()


@router.get("/projects")
async def list_projects():
    projects = engine.list_projects()
    return {"projects": projects, "total": len(projects)}


@router.get("/changes")
async def list_changes(project_id: str | None = Query(None), status: str | None = Query(None)):
    changes = engine.tracker.get_changes(project_id=project_id, status=status)
    pending = len([c for c in changes if c.get("status") == "draft"])
    preview = len([c for c in changes if c.get("status") == "preview"])
    return {"changes": changes, "total": len(changes), "pending": pending, "preview": preview}


@router.get("/previews")
async def list_previews(project_id: str | None = Query(None)):
    previews = engine.workspace_mgr.list_workspaces(project_id=project_id)
    return {"previews": previews, "total": len(previews), "active": len(previews)}


@router.post("/generate-pr", response_model=GeneratePRResponse)
async def generate_pr(request: GeneratePRRequest):
    result = engine.generate_pr_workflow(
        project_id=request.project_id,
        change_ids=request.change_ids,
        title=request.title,
        description=request.description,
    )
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "PR generation failed"))
    return GeneratePRResponse(
        pr_draft=result["pr_draft"],
        branch=result["branch"],
        preview_workspace=result["preview_workspace"],
        markdown_body=result["markdown_body"],
        success=True,
        message=result["message"],
    )


@router.get("/status", response_model=RepoStatusResponse)
async def get_status():
    status = engine.get_status()
    return RepoStatusResponse(**status)
