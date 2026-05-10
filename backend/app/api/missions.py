from fastapi import APIRouter
from app.missions.mission_registry import get_project_missions

router = APIRouter()


@router.get("/missions/{project_id}")
def get_missions(project_id: str):
    return get_project_missions(project_id)
