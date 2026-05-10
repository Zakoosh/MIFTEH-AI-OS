from fastapi import APIRouter
from app.brain.context_builder import build_project_context

router = APIRouter()


@router.get("/brain/context/{project_id}")
def get_project_context(project_id: str):
    return build_project_context(project_id)
