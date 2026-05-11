from fastapi import APIRouter

from app.missions.models import MissionRequest
from app.missions.runner import execute_mission, get_mission_execution, get_mission_history
from app.missions.planner import list_available_missions

router = APIRouter(prefix="/missions", tags=["mission-engine"])


@router.post("/run")
def run_mission(request: MissionRequest):
    return execute_mission(request)


@router.get("/history")
def mission_history():
    return get_mission_history()


@router.get("/available")
def available_missions():
    return {"missions": list_available_missions()}


@router.get("/execution/{execution_id}")
def get_execution(execution_id: str):
    return get_mission_execution(execution_id)
