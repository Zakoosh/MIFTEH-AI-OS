from app.decision.execution_plans import build_execution_plan
from app.decision.mission_selector import select_project_missions, top_decision
from app.decision.models import ProjectDecision
from app.decision.strategy import continuous_focus_areas


def build_project_decision(project: object, profile: dict) -> ProjectDecision:
    decisions = select_project_missions(project, profile)
    selected = top_decision(decisions)
    execution_plan = build_execution_plan(selected) if selected else None

    return ProjectDecision(
        project_id=project.project_id,
        project=project.name,
        recommended_mission=selected.mission_id if selected else "",
        priority=selected.priority if selected else "low",
        estimated_impact=selected.impact_score if selected else 0,
        automation_readiness=project.health.automation_readiness,
        continuous_improvement_areas=continuous_focus_areas(project.project_id),
        decisions=decisions,
        execution_plan=execution_plan,
        warnings=project.warnings,
    )


def flatten_project_decisions(project_decisions: list[ProjectDecision]):
    decisions = []
    for project in project_decisions:
        decisions.extend(project.decisions)

    return sorted(decisions, key=lambda item: item.decision_score, reverse=True)


def flatten_execution_plans(project_decisions: list[ProjectDecision]):
    return [
        project.execution_plan
        for project in project_decisions
        if project.execution_plan is not None
    ]
