from app.decision.models import (
    DecisionOverview,
    DecisionPriorityList,
    DecisionRecommendationList,
    ExecutionPlanList,
    ProjectDecision,
)
from app.decision.planner import (
    build_project_decision,
    flatten_execution_plans,
    flatten_project_decisions,
)
from app.intelligence.analyzer import analyze_project_profile, analyze_projects
from app.intelligence.project_profile import collect_project_profile, collect_project_profiles


def _project_decisions() -> list[ProjectDecision]:
    profiles = collect_project_profiles()
    decisions: list[ProjectDecision] = []

    for profile in profiles:
        intelligence = analyze_project_profile(profile)
        decisions.append(build_project_decision(intelligence, profile))

    return decisions


def decision_overview() -> DecisionOverview:
    decisions = _project_decisions()
    mission_decisions = flatten_project_decisions(decisions)
    recommended = mission_decisions[0] if mission_decisions else None

    readiness = 0
    intelligence_projects = analyze_projects()
    if intelligence_projects:
        readiness = round(
            sum(project.health.automation_readiness for project in intelligence_projects)
            / len(intelligence_projects)
        )

    return DecisionOverview(
        projects_count=len(decisions),
        recommended_project=recommended.project_id if recommended else "",
        recommended_mission=recommended.mission_id if recommended else "",
        priority=recommended.priority if recommended else "low",
        estimated_impact=recommended.impact_score if recommended else 0,
        automation_readiness=readiness,
        decisions=decisions,
    )


def decision_plans() -> ExecutionPlanList:
    return ExecutionPlanList(plans=flatten_execution_plans(_project_decisions()))


def decision_project(project_id: str) -> ProjectDecision | None:
    profile = collect_project_profile(project_id)
    if profile is None:
        return None

    intelligence = analyze_project_profile(profile)
    return build_project_decision(intelligence, profile)


def decision_recommendations() -> DecisionRecommendationList:
    return DecisionRecommendationList(
        recommendations=flatten_project_decisions(_project_decisions())
    )


def decision_priorities() -> DecisionPriorityList:
    priorities = DecisionPriorityList()

    for decision in flatten_project_decisions(_project_decisions()):
        if decision.priority == "critical":
            priorities.critical.append(decision)
        elif decision.priority == "high":
            priorities.high.append(decision)
        elif decision.priority == "medium":
            priorities.medium.append(decision)
        else:
            priorities.low.append(decision)

    return priorities
