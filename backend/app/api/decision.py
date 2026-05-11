from fastapi import APIRouter

from app.decision.engine import (
    decision_overview,
    decision_plans,
    decision_priorities,
    decision_project,
    decision_recommendations,
)


router = APIRouter(prefix="/decision", tags=["decision"])


@router.get("/overview")
def get_decision_overview():
    return decision_overview().model_dump()


@router.get("/plans")
def get_decision_plans():
    return decision_plans().model_dump()


@router.get("/project/{project_id}")
def get_decision_project(project_id: str):
    project = decision_project(project_id)

    if project is None:
        return {
            "success": False,
            "error": f"Project '{project_id}' not found",
        }

    return project.model_dump()


@router.get("/recommendations")
def get_decision_recommendations():
    return decision_recommendations().model_dump()


@router.get("/priorities")
def get_decision_priorities():
    return decision_priorities().model_dump()
