from fastapi import APIRouter
from app.brain.context_builder import build_project_context
from app.brain.health_report import generate_health_report
from app.brain.security_scanner import scan_security_details

router = APIRouter()


@router.get("/brain/context/{project_id}")
def get_project_context(project_id: str):
    return build_project_context(project_id)


@router.get("/brain/health/{project_id}")
def get_project_health(project_id: str):
    return generate_health_report(project_id)


@router.get("/brain/security/{project_id}")
def get_project_security(project_id: str):
    return scan_security_details(project_id)
