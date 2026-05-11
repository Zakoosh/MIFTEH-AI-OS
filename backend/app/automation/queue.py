import asyncio

from app.automation.history import load_tasks, save_tasks
from app.automation.models import (
    AutomationPolicy,
    AutomationTask,
    TASK_STATUS_PENDING,
    TASK_STATUS_RUNNING,
)
from app.automation.policies import DEFAULT_POLICY, can_claim_task
from app.automation.triggers import iso_now


_TASK_LOCK = asyncio.Lock()


def _replace_task(tasks: list[AutomationTask], updated: AutomationTask) -> list[AutomationTask]:
    return [
        updated if task.task_id == updated.task_id else task
        for task in tasks
    ]


async def list_tasks() -> list[AutomationTask]:
    async with _TASK_LOCK:
        return load_tasks()


async def get_task(task_id: str) -> AutomationTask | None:
    async with _TASK_LOCK:
        for task in load_tasks():
            if task.task_id == task_id:
                return task
    return None


async def save_task(task: AutomationTask) -> AutomationTask:
    async with _TASK_LOCK:
        tasks = load_tasks()
        task.updated_at = iso_now()

        if any(existing.task_id == task.task_id for existing in tasks):
            tasks = _replace_task(tasks, task)
        else:
            tasks.append(task)

        save_tasks(tasks)
        return task


async def running_count() -> int:
    async with _TASK_LOCK:
        return sum(1 for task in load_tasks() if task.status == TASK_STATUS_RUNNING)


async def claim_task(
    task_id: str,
    policy: AutomationPolicy = DEFAULT_POLICY,
    force: bool = False,
) -> tuple[AutomationTask | None, str | None]:
    async with _TASK_LOCK:
        tasks = load_tasks()
        task = next((item for item in tasks if item.task_id == task_id), None)

        if task is None:
            return None, f"Task '{task_id}' not found"

        running = sum(1 for item in tasks if item.status == TASK_STATUS_RUNNING)
        policy_error = can_claim_task(task, running, policy=policy, force=force)
        if policy_error:
            return None, policy_error

        task.status = TASK_STATUS_RUNNING
        task.last_run_at = iso_now()
        task.updated_at = task.last_run_at
        save_tasks(_replace_task(tasks, task))
        return task, None


async def complete_task(task: AutomationTask) -> AutomationTask:
    async with _TASK_LOCK:
        tasks = load_tasks()
        task.updated_at = iso_now()
        save_tasks(_replace_task(tasks, task))
        return task


async def pending_tasks() -> list[AutomationTask]:
    async with _TASK_LOCK:
        return [
            task
            for task in load_tasks()
            if task.enabled and task.status == TASK_STATUS_PENDING
        ]
