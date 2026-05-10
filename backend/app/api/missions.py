from fastapi import APIRouter
from app.missions.mission_registry import get_project_missions
from app.missions.mission_runner import run_project_mission

router = APIRouter()


@router.get("/missions/{project_id}")
def get_missions(project_id: str):
    return get_project_missions(project_id)


@router.get("/missions/{project_id}/run/{mission_id}")
def run_mission(project_id: str, mission_id: str):
    return run_project_mission(project_id, mission_id)
