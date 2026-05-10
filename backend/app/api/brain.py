from fastapi import APIRouter
from app.brain.context_builder import build_project_context
from app.brain.health_report import generate_health_report
from app.brain.security_scanner import scan_security_details
from app.brain.agent_matcher import match_agents_for_project
from app.brain.workflow_preview import build_workflow_preview

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


@router.get("/brain/match-agents/{project_id}")
def get_project_agent_matches(project_id: str):
    return match_agents_for_project(project_id)


@router.get("/brain/workflow-preview/{project_id}")
def get_workflow_preview(project_id: str):
    return build_workflow_preview(project_id)
