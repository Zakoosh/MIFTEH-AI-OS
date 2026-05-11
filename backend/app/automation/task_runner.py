import asyncio

from app.automation.history import append_history
from app.automation.models import (
    AutomationHistoryEntry,
    AutomationTask,
    AutomationTaskRunResult,
    TASK_STATUS_COMPLETED,
    TASK_STATUS_FAILED,
)
from app.automation.triggers import add_minutes, iso_now, safe_id, seconds_between
from app.engine.report_dashboard import reports_dashboard
from app.git.diff_manager import generate_diff
from app.git.status_manager import get_repository_status
from app.missions.models import MissionRequest
from app.missions.runner import execute_mission


async def _git_snapshot(project_id: str) -> tuple[dict, dict]:
    status = await asyncio.to_thread(get_repository_status, project_id)
    diff = await asyncio.to_thread(generate_diff, project_id)

    return (
        status.model_dump(),
        diff.model_dump(exclude={"diff"}),
    )


def _mission_succeeded(result: dict) -> bool:
    return "error" not in result and bool(result.get("execution_id"))


async def run_claimed_task(task: AutomationTask) -> AutomationTaskRunResult:
    started_at = iso_now()
    attempt = task.retry_count + 1
    git_status: dict = {}
    git_diff: dict = {}
    mission_result: dict = {}
    reports_summary: dict = {}
    error: str | None = None

    try:
        git_status, git_diff = await _git_snapshot(task.project_id)

        mission_result = await asyncio.to_thread(
            execute_mission,
            MissionRequest(
                project_id=task.project_id,
                mission_id=task.mission_id,
                agent_limit=task.agent_limit,
            ),
        )

        reports_summary = await asyncio.to_thread(reports_dashboard)

        if not _mission_succeeded(mission_result):
            error = mission_result.get("error", "Mission execution failed")
    except Exception as exc:
        error = str(exc)

    completed_at = iso_now()
    success = error is None

    task.status = TASK_STATUS_COMPLETED if success else TASK_STATUS_FAILED
    task.last_completed_at = completed_at
    task.last_error = error
    task.last_execution_id = mission_result.get("execution_id")
    task.retry_count = 0 if success else attempt
    task.next_run_at = add_minutes(
        completed_at,
        task.interval_minutes if success else task.cooldown_minutes,
    )

    history = AutomationHistoryEntry(
        history_id=(
            f"{safe_id(task.project_id)}_"
            f"{safe_id(task.mission_id)}_"
            f"{safe_id(started_at)}"
        ),
        task_id=task.task_id,
        mission_id=task.mission_id,
        project_id=task.project_id,
        status=task.status,
        attempt=attempt,
        started_at=started_at,
        completed_at=completed_at,
        duration_seconds=seconds_between(started_at, completed_at),
        execution_id=task.last_execution_id,
        error=error,
        mission_result=mission_result,
        git_status=git_status,
        git_diff=git_diff,
        reports_summary=reports_summary,
    )

    await asyncio.to_thread(append_history, history)

    return AutomationTaskRunResult(
        success=success,
        task=task,
        history=history,
        error=error,
    )
