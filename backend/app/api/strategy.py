from fastapi import APIRouter

from app.strategy.engine import (
    strategy_opportunities,
    strategy_overview,
    strategy_project,
    strategy_projects,
    strategy_roadmaps,
)


router = APIRouter(prefix="/strategy", tags=["strategy"])


@router.get("/overview")
def get_strategy_overview():
    return strategy_overview().model_dump()


@router.get("/projects")
def get_strategy_projects():
    return strategy_projects().model_dump()


@router.get("/project/{project_id}")
def get_strategy_project(project_id: str):
    project = strategy_project(project_id)

    if project is None:
        return {
            "success": False,
            "error": f"Project '{project_id}' not found",
        }

    return project.model_dump()


@router.get("/roadmaps")
def get_strategy_roadmaps():
    return strategy_roadmaps().model_dump()


@router.get("/opportunities")
def get_strategy_opportunities():
    return strategy_opportunities().model_dump()
