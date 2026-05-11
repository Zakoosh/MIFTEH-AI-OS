from datetime import datetime, timezone

from app.decision.models import DecisionConstraint


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed


def _mission_history(profile: dict, mission_id: str) -> list[dict]:
    return [
        item for item in profile.get("mission_history", [])
        if item.get("mission_id") == mission_id
    ]


def _automation_history(profile: dict, mission_id: str) -> list[dict]:
    return [
        item for item in profile.get("automation_history", [])
        if item.get("mission_id") == mission_id
    ]


def evaluate_constraints(
    project: object,
    profile: dict,
    mission_id: str,
) -> list[DecisionConstraint]:
    constraints = [
        DecisionConstraint(
            name="advisory_only",
            allowed=True,
            severity="info",
            message="Decision layer recommends plans only; it does not execute missions.",
        )
    ]

    if project.workspace.error:
        constraints.append(DecisionConstraint(
            name="workspace_warning",
            allowed=True,
            severity="warning",
            message=project.workspace.error,
        ))

    if project.signals.git_available and project.signals.git_clean is False:
        constraints.append(DecisionConstraint(
            name="git_dirty",
            allowed=False,
            severity="warning",
            message="Uncommitted git changes should be reviewed before automated scheduling.",
        ))

    mission_runs = _mission_history(profile, mission_id)
    recent_runs = mission_runs[:3]
    recent_failures = sum(
        1 for item in recent_runs
        if "fail" in str(item.get("status", "")).lower()
    )
    if recent_runs and recent_failures == len(recent_runs):
        constraints.append(DecisionConstraint(
            name="repeated_failure_avoidance",
            allowed=False,
            severity="warning",
            message="Recent runs for this mission failed repeatedly; review before retrying.",
        ))

    latest_run = next((item for item in mission_runs if item.get("completed_at") or item.get("started_at")), None)
    latest_at = _parse_datetime(
        (latest_run or {}).get("completed_at") or (latest_run or {}).get("started_at")
    )
    if latest_at is not None:
        elapsed_minutes = (datetime.now(timezone.utc) - latest_at).total_seconds() / 60
        if elapsed_minutes < 60:
            constraints.append(DecisionConstraint(
                name="cooldown",
                allowed=False,
                severity="info",
                message="Mission ran recently; wait for cooldown before scheduling another run.",
            ))

    recent_automation_failures = sum(
        1 for item in _automation_history(profile, mission_id)[:3]
        if "fail" in str(item.get("status", "")).lower()
    )
    if recent_automation_failures >= 2:
        constraints.append(DecisionConstraint(
            name="automation_failure_guard",
            allowed=False,
            severity="warning",
            message="Automation has failed recently for this mission; prefer manual review.",
        ))

    return constraints


def has_blocking_constraints(constraints: list[DecisionConstraint]) -> bool:
    return any(not constraint.allowed for constraint in constraints)
