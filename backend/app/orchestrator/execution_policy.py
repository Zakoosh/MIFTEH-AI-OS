from app.orchestrator.models import OrchestrationConstraint


MAX_RECOMMENDED_MISSIONS = 5
DEFAULT_COOLDOWN_MINUTES = 180


def normalized_max_missions(value: int) -> int:
    if value <= 0:
        return MAX_RECOMMENDED_MISSIONS

    return min(value, MAX_RECOMMENDED_MISSIONS)


def base_execution_constraints(dry_run: bool) -> list[OrchestrationConstraint]:
    constraints = [
        OrchestrationConstraint(
            name="no_autonomous_code_application",
            allowed=True,
            severity="info",
            message="The orchestrator may recommend missions but never applies code changes.",
        ),
        OrchestrationConstraint(
            name="no_auto_merge_or_push",
            allowed=True,
            severity="info",
            message="The orchestrator does not merge, push, or force git operations.",
        ),
        OrchestrationConstraint(
            name="advisory_scheduler",
            allowed=True,
            severity="info",
            message="Scheduler actions are suggestions until explicitly executed by a separate approved layer.",
        ),
    ]

    if not dry_run:
        constraints.append(OrchestrationConstraint(
            name="autonomous_execution_disabled",
            allowed=False,
            severity="warning",
            message="Non-dry-run orchestration is disabled for this rule-based layer.",
        ))

    return constraints


def scheduler_action(optimization_score: int, automation_readiness: int, blocked: bool) -> str:
    if blocked:
        return "manual_review"

    if optimization_score >= 80 and automation_readiness >= 70:
        return "candidate_for_interval_schedule"

    if optimization_score >= 60:
        return "candidate_for_manual_run"

    return "monitor"
