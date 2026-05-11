from app.automation import queue
from app.automation.models import (
    AutomationTask,
    AutomationTaskList,
    SCHEDULE_TYPE_INTERVAL,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
    TASK_STATUS_PENDING,
)
from app.automation.policies import validate_interval_schedule
from app.automation.schemas import ScheduleRequest
from app.automation.triggers import add_minutes, is_due, iso_now, safe_id


def _task_id(project_id: str, mission_id: str) -> str:
    timestamp = safe_id(iso_now())
    return f"{safe_id(project_id)}_{safe_id(mission_id)}_{timestamp}"


async def schedule_interval_task(request: ScheduleRequest) -> dict:
    error = validate_interval_schedule(
        project_id=request.project_id,
        mission_id=request.mission_id,
        interval_minutes=request.interval_minutes,
        max_retries=request.max_retries,
        cooldown_minutes=request.cooldown_minutes,
        agent_limit=request.agent_limit,
    )

    if error:
        return {"success": False, "error": error}

    now = iso_now()
    task = AutomationTask(
        task_id=_task_id(request.project_id, request.mission_id),
        mission_id=request.mission_id,
        project_id=request.project_id,
        schedule_type=SCHEDULE_TYPE_INTERVAL,
        interval_minutes=request.interval_minutes,
        enabled=request.enabled,
        status=TASK_STATUS_PENDING,
        retry_count=0,
        max_retries=request.max_retries,
        cooldown_minutes=request.cooldown_minutes,
        agent_limit=request.agent_limit,
        created_at=now,
        updated_at=now,
        next_run_at=now if request.enabled else add_minutes(now, request.interval_minutes),
    )

    saved = await queue.save_task(task)
    return {"success": True, "task": saved.model_dump()}


async def refresh_due_tasks() -> None:
    tasks = await queue.list_tasks()

    for task in tasks:
        if not task.enabled:
            continue

        if task.status == TASK_STATUS_COMPLETED and is_due(task.next_run_at):
            task.status = TASK_STATUS_PENDING
            task.last_error = None
            await queue.save_task(task)

        if (
            task.status == TASK_STATUS_FAILED
            and task.retry_count < task.max_retries
            and is_due(task.next_run_at)
        ):
            task.status = TASK_STATUS_PENDING
            await queue.save_task(task)


async def list_scheduled_tasks() -> AutomationTaskList:
    await refresh_due_tasks()
    tasks = await queue.list_tasks()
    counts = {
        TASK_STATUS_PENDING: 0,
        "running": 0,
        TASK_STATUS_COMPLETED: 0,
        TASK_STATUS_FAILED: 0,
    }

    for task in tasks:
        counts[task.status] = counts.get(task.status, 0) + 1

    return AutomationTaskList(
        tasks=tasks,
        pending=counts.get(TASK_STATUS_PENDING, 0),
        running=counts.get("running", 0),
        completed=counts.get(TASK_STATUS_COMPLETED, 0),
        failed=counts.get(TASK_STATUS_FAILED, 0),
    )


async def toggle_task(task_id: str, enabled: bool | None = None) -> dict:
    task = await queue.get_task(task_id)

    if task is None:
        return {"success": False, "error": f"Task '{task_id}' not found"}

    task.enabled = (not task.enabled) if enabled is None else enabled
    task.updated_at = iso_now()

    if task.enabled and task.status in {TASK_STATUS_COMPLETED, TASK_STATUS_FAILED}:
        task.status = TASK_STATUS_PENDING
        task.next_run_at = iso_now()

    saved = await queue.save_task(task)
    return {"success": True, "task": saved.model_dump()}
