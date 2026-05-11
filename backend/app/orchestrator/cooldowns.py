from datetime import datetime, timezone

from app.orchestrator.execution_policy import DEFAULT_COOLDOWN_MINUTES
from app.orchestrator.models import OrchestrationConstraint


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed


def cooldown_constraint(
    project_id: str,
    mission_id: str,
    cycles: list,
    cooldown_minutes: int = DEFAULT_COOLDOWN_MINUTES,
) -> OrchestrationConstraint:
    latest: datetime | None = None

    for cycle in cycles:
        for recommendation in cycle.selected_recommendations:
            if recommendation.project_id == project_id and recommendation.mission_id == mission_id:
                completed_at = parse_datetime(cycle.completed_at)
                if completed_at and (latest is None or completed_at > latest):
                    latest = completed_at

    if latest is None:
        return OrchestrationConstraint(
            name="cooldown",
            allowed=True,
            severity="info",
            message="No previous orchestration cycle found for this mission.",
        )

    elapsed_minutes = (datetime.now(timezone.utc) - latest).total_seconds() / 60
    if elapsed_minutes < cooldown_minutes:
        remaining = round(cooldown_minutes - elapsed_minutes)
        return OrchestrationConstraint(
            name="cooldown",
            allowed=False,
            severity="info",
            message=f"Mission is cooling down for approximately {remaining} more minutes.",
        )

    return OrchestrationConstraint(
        name="cooldown",
        allowed=True,
        severity="info",
        message="Cooldown window has passed.",
    )
