from app.automation import queue
from app.automation.models import AutomationTaskRunResult
from app.automation.scheduler import refresh_due_tasks
from app.automation.task_runner import run_claimed_task


async def run_task(task_id: str, force: bool = True) -> AutomationTaskRunResult:
    await refresh_due_tasks()
    task, error = await queue.claim_task(task_id, force=force)

    if error or task is None:
        return AutomationTaskRunResult(success=False, error=error)

    result = await run_claimed_task(task)

    if result.task is not None:
        await queue.complete_task(result.task)

    return result
