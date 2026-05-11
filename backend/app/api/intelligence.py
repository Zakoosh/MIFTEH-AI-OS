from fastapi import APIRouter

from app.intelligence.analyzer import (
    intelligence_overview,
    intelligence_project,
    intelligence_projects,
    intelligence_recommendations,
    intelligence_trends,
)


router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.get("/overview")
def get_intelligence_overview():
    return intelligence_overview().model_dump()


@router.get("/projects")
def get_intelligence_projects():
    return intelligence_projects().model_dump()


@router.get("/project/{project_id}")
def get_intelligence_project(project_id: str):
    project = intelligence_project(project_id)

    if project is None:
        return {
            "success": False,
            "error": f"Project '{project_id}' not found",
        }

    return project.model_dump()


@router.get("/recommendations")
def get_intelligence_recommendations():
    return intelligence_recommendations().model_dump()


@router.get("/trends")
def get_intelligence_trends():
    return intelligence_trends().model_dump()
