from app.orchestrator.models import OrchestrationConstraint


def convert_decision_constraints(decision: object) -> list[OrchestrationConstraint]:
    constraints: list[OrchestrationConstraint] = []

    for constraint in getattr(decision, "constraints", []):
        constraints.append(OrchestrationConstraint(
            name=constraint.name,
            allowed=constraint.allowed,
            severity=constraint.severity,
            message=constraint.message,
        ))

    return constraints


def repeated_failure_constraint(decision: object) -> OrchestrationConstraint:
    if "failure" in " ".join(getattr(decision, "reasons", [])).lower():
        return OrchestrationConstraint(
            name="failure_review_required",
            allowed=False,
            severity="warning",
            message="Recent failures were detected; review reports before scheduling this mission.",
        )

    return OrchestrationConstraint(
        name="failure_review_required",
        allowed=True,
        severity="info",
        message="No repeated failure guard triggered.",
    )


def dashboard_continuous_improvement_constraint(decision: object) -> OrchestrationConstraint:
    if decision.project_id == "mifteh" and decision.mission_id == "improve-dashboard":
        return OrchestrationConstraint(
            name="dashboard_continuous_improvement",
            allowed=True,
            severity="info",
            message="Dashboard improvement remains an ongoing orchestration target.",
        )

    return OrchestrationConstraint(
        name="dashboard_continuous_improvement",
        allowed=True,
        severity="info",
        message="Project remains eligible for continuous improvement cycles.",
    )


def has_blocking_constraint(constraints: list[OrchestrationConstraint]) -> bool:
    return any(not constraint.allowed for constraint in constraints)
