from app.decision.constraints import evaluate_constraints, has_blocking_constraints
from app.decision.models import MissionDecision
from app.decision.prioritizer import (
    calculate_effort_penalty,
    calculate_impact,
    calculate_urgency,
    decision_score,
    sort_decisions,
)
from app.decision.strategy import mission_improvement_areas
from app.missions.planner import resolve_mission


def _agent_names(project_id: str, mission_id: str) -> list[str]:
    mission = resolve_mission(project_id, mission_id)
    if mission is None:
        return []

    return [
        path.split("/")[-1].replace(".md", "")
        for path in mission.get("agent_paths", [])
    ]


def select_project_missions(project: object, profile: dict) -> list[MissionDecision]:
    decisions: list[MissionDecision] = []

    for recommendation in project.recommendations:
        agents = _agent_names(project.project_id, recommendation.mission_id)
        improvement_areas = mission_improvement_areas(
            recommendation.mission_id,
            recommendation.title,
        )
        constraints = evaluate_constraints(project, profile, recommendation.mission_id)
        blocked = has_blocking_constraints(constraints)
        urgency_score = calculate_urgency(project, recommendation)
        impact_score = calculate_impact(project, recommendation, improvement_areas)
        effort_score = calculate_effort_penalty(len(agents))
        score = decision_score(
            urgency_score=urgency_score,
            impact_score=impact_score,
            effort_score=effort_score,
            automation_readiness=project.health.automation_readiness,
            blocked=blocked,
        )

        decisions.append(MissionDecision(
            project_id=project.project_id,
            project=project.name,
            mission_id=recommendation.mission_id,
            title=recommendation.title,
            urgency_score=urgency_score,
            impact_score=impact_score,
            effort_score=effort_score,
            automation_readiness=project.health.automation_readiness,
            decision_score=score,
            recommended_agents=agents,
            improvement_areas=improvement_areas,
            reasons=recommendation.reasons,
            constraints=constraints,
            blocked=blocked,
        ))

    return sort_decisions(decisions)


def top_decision(decisions: list[MissionDecision]) -> MissionDecision | None:
    if not decisions:
        return None

    unblocked = [decision for decision in decisions if not decision.blocked]
    return (unblocked or decisions)[0]
