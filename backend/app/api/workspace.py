from fastapi import APIRouter

from app.projects.registry import (
    list_projects,
    get_project,
    get_workspace_status,
    refresh_projects,
)
from app.projects.project_mapper import (
    get_project_agents_detail,
    get_project_missions_detail,
)

router = APIRouter(prefix="/workspace", tags=["workspace"])


@router.get("/projects")
def get_all_projects():
    projects = list_projects()
    return {
        "total": len(projects),
        "projects": [p.model_dump() for p in projects],
    }


@router.get("/projects/status")
def workspace_status():
    return get_workspace_status().model_dump()


@router.get("/projects/refresh")
def refresh():
    projects = refresh_projects()
    return {
        "refreshed": True,
        "total": len(projects),
        "projects": [p.model_dump() for p in projects.values()],
    }


@router.get("/projects/{project_id}")
def get_single_project(project_id: str):
    project = get_project(project_id)
    if project is None:
        return {"error": f"Project '{project_id}' not found"}
    return project.model_dump()


@router.get("/projects/{project_id}/agents")
def project_agents(project_id: str):
    project = get_project(project_id)
    if project is None:
        return {"error": f"Project '{project_id}' not found"}

    agents = get_project_agents_detail(project_id, project.project_type)
    return {
        "project_id": project_id,
        "project_type": project.project_type,
        "agents_count": len(agents),
        "agents": agents,
    }


@router.get("/projects/{project_id}/missions")
def project_missions(project_id: str):
    project = get_project(project_id)
    if project is None:
        return {"error": f"Project '{project_id}' not found"}

    missions = get_project_missions_detail(project_id)
    return {
        "project_id": project_id,
        "missions_count": len(missions),
        "missions": missions,
    }
