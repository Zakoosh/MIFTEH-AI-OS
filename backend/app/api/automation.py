import asyncio

from fastapi import APIRouter

from app.automation.history import load_history
from app.automation.models import AutomationHistoryList
from app.automation.scheduler import (
    list_scheduled_tasks,
    schedule_interval_task,
    toggle_task,
)
from app.automation.schemas import ScheduleRequest, ToggleTaskRequest
from app.automation.worker import run_task


router = APIRouter(prefix="/automation", tags=["automation"])


@router.post("/schedule")
async def schedule_task(request: ScheduleRequest):
    return await schedule_interval_task(request)


@router.get("/tasks")
async def automation_tasks():
    return (await list_scheduled_tasks()).model_dump()


@router.get("/history")
async def automation_history():
    entries = await asyncio.to_thread(load_history)
    return AutomationHistoryList(total=len(entries), entries=entries).model_dump()


@router.post("/task/{task_id}/run")
async def run_automation_task(task_id: str):
    return (await run_task(task_id, force=True)).model_dump()


@router.post("/task/{task_id}/toggle")
async def toggle_automation_task(task_id: str, request: ToggleTaskRequest):
    return await toggle_task(task_id, enabled=request.enabled)
