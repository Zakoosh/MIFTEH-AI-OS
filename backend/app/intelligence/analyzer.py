from app.intelligence.health_engine import (
    average_automation_readiness,
    average_health,
    build_health,
    highest_risk_project,
)
from app.intelligence.models import (
    IntelligenceCollection,
    IntelligenceOverview,
    ProjectIntelligence,
    RecommendationCollection,
    TrendCollection,
    WorkspaceMetadata,
)
from app.intelligence.priorities import project_priorities
from app.intelligence.project_profile import collect_project_profile, collect_project_profiles
from app.intelligence.recommendations import flatten_recommendations, recommend_for_project
from app.intelligence.trends import analyze_trend


def analyze_project_profile(profile: dict) -> ProjectIntelligence:
    signals, health = build_health(profile)
    recommendations = recommend_for_project(profile, signals, health)
    trend = analyze_trend(profile, signals)
    workspace = WorkspaceMetadata.model_validate(profile.get("workspace", {}))
    warnings = []

    if workspace.error:
        warnings.append(workspace.error)

    if profile.get("git_state", {}).get("error"):
        warnings.append(profile["git_state"]["error"])

    return ProjectIntelligence(
        project_id=profile["project_id"],
        name=profile.get("name", profile["project_id"]),
        project_type=profile.get("project_type", ""),
        health=health,
        signals=signals,
        priorities=project_priorities(profile, signals, health),
        recommendations=recommendations,
        trend=trend,
        workspace=workspace,
        warnings=warnings,
    )


def analyze_projects() -> list[ProjectIntelligence]:
    return [
        analyze_project_profile(profile)
        for profile in collect_project_profiles()
    ]


def intelligence_overview() -> IntelligenceOverview:
    projects = analyze_projects()
    recommendations = flatten_recommendations(projects)

    return IntelligenceOverview(
        overall_health=average_health(projects),
        highest_risk_project=highest_risk_project(projects),
        recommended_next_mission=recommendations[0].mission_id if recommendations else "",
        automation_readiness=average_automation_readiness(projects),
        projects_count=len(projects),
        projects=projects,
    )


def intelligence_projects() -> IntelligenceCollection:
    return IntelligenceCollection(projects=analyze_projects())


def intelligence_project(project_id: str) -> ProjectIntelligence | None:
    profile = collect_project_profile(project_id)
    if profile is None:
        return None

    return analyze_project_profile(profile)


def intelligence_recommendations() -> RecommendationCollection:
    return RecommendationCollection(
        recommendations=flatten_recommendations(analyze_projects())
    )


def intelligence_trends() -> TrendCollection:
    return TrendCollection(
        trends=[project.trend for project in analyze_projects()]
    )
