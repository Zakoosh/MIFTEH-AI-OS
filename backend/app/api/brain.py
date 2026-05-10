from fastapi import APIRouter
from app.brain.context_builder import build_project_context
from app.brain.health_report import generate_health_report

router = APIRouter()


@router.get("/brain/context/{project_id}")
def get_project_context(project_id: str):
    return build_project_context(project_id)


@router.get("/brain/health/{project_id}")
def get_project_health(project_id: str):
    return generate_health_report(project_id)
