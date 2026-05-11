from app.decision.models import MissionDecision
from app.decision.strategy import priority_from_score


def calculate_urgency(project: object, recommendation: object) -> int:
    score = 20

    score += min(project.health.risk_score, 40)

    if project.trend.neglected:
        score += 20

    if project.trend.failure_trend == "worsening":
        score += 15
    elif project.trend.failure_trend == "watch":
        score += 8

    if recommendation.priority in {"critical", "high"}:
        score += 15

    return min(score, 100)


def calculate_impact(project: object, recommendation: object, improvement_areas: list[str]) -> int:
    score = recommendation.score

    if "security" in [area.lower() for area in improvement_areas]:
        score += 8

    if "performance" in [area.lower() for area in improvement_areas]:
        score += 6

    if "SEO".lower() in [area.lower() for area in improvement_areas]:
        score += 6

    if project.health.overall_health < 60:
        score += 8

    return min(score, 100)


def calculate_effort_penalty(agent_count: int) -> int:
    if agent_count <= 2:
        return 15
    if agent_count <= 5:
        return 35
    return 55


def decision_score(
    urgency_score: int,
    impact_score: int,
    effort_score: int,
    automation_readiness: int,
    blocked: bool,
) -> int:
    score = round(
        urgency_score * 0.35
        + impact_score * 0.35
        + automation_readiness * 0.20
        + (100 - effort_score) * 0.10
    )

    if blocked:
        score -= 20

    return max(0, min(score, 100))


def sort_decisions(decisions: list[MissionDecision]) -> list[MissionDecision]:
    for decision in decisions:
        decision.priority = priority_from_score(decision.decision_score)

    return sorted(decisions, key=lambda item: item.decision_score, reverse=True)
