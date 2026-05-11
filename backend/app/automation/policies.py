from app.automation.models import AutomationPolicy, AutomationTask
from app.automation.triggers import is_due, parse_iso_datetime, utc_now
from app.missions.planner import resolve_mission


DEFAULT_POLICY = AutomationPolicy()


def validate_interval_schedule(
    project_id: str,
    mission_id: str,
    interval_minutes: int,
    max_retries: int,
    cooldown_minutes: int,
    agent_limit: int,
) -> str | None:
    if interval_minutes <= 0:
        return "interval_minutes must be greater than 0"

    if max_retries < 0:
        return "max_retries cannot be negative"

    if cooldown_minutes < 0:
        return "cooldown_minutes cannot be negative"

    if agent_limit < 0:
        return "agent_limit cannot be negative"

    if resolve_mission(project_id, mission_id) is None:
        return f"Mission '{mission_id}' not found for project '{project_id}'"

    return None


def can_claim_task(
    task: AutomationTask,
    running_count: int,
    policy: AutomationPolicy = DEFAULT_POLICY,
    force: bool = False,
) -> str | None:
    if task.status == "running":
        return "Task is already running"

    if running_count >= policy.max_concurrent_tasks:
        return "Max concurrent task limit reached"

    if not task.enabled and not force:
        return "Task is disabled"

    if task.status == "failed" and task.retry_count >= task.max_retries and not force:
        return "Task retry limit reached"

    if not force and not is_due(task.next_run_at):
        return "Task is not due yet"

    if task.last_completed_at:
        completed_at = parse_iso_datetime(task.last_completed_at)
        if completed_at is not None:
            elapsed = (utc_now() - completed_at).total_seconds()
            cooldown_seconds = task.cooldown_minutes * 60
            if elapsed < cooldown_seconds and not force:
                return "Task is cooling down"

    return None
