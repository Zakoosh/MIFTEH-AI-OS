from app.memory_ai.learning_engine import build_memory_snapshot
from app.orchestrator.engine import orchestrator_recommendations
from app.strategy.models import StrategicOpportunity


def _priority(score: int) -> str:
    if score >= 85:
        return "high"
    if score >= 60:
        return "medium"
    return "low"


def detect_project_opportunities(project: object) -> list[StrategicOpportunity]:
    opportunities: list[StrategicOpportunity] = []

    for recommendation in project.recommendations[:3]:
        opportunities.append(StrategicOpportunity(
            project_id=project.project_id,
            opportunity=f"Advance {recommendation.mission_id} to improve {project.name}",
            domain="growth",
            priority=recommendation.priority,
            confidence=round(recommendation.score / 100, 2),
            evidence=recommendation.reasons[:4],
        ))

    if project.health.risk_score >= 50:
        opportunities.append(StrategicOpportunity(
            project_id=project.project_id,
            opportunity="Reduce risk before scaling growth initiatives",
            domain="security",
            priority="high",
            confidence=round(project.health.risk_score / 100, 2),
            evidence=project.priorities[:4],
        ))

    if project.health.automation_readiness >= 70:
        opportunities.append(StrategicOpportunity(
            project_id=project.project_id,
            opportunity="Convert recurring optimization missions into scheduled workflows",
            domain="automation",
            priority="medium",
            confidence=round(project.health.automation_readiness / 100, 2),
            evidence=["Automation readiness is above threshold"],
        ))

    return opportunities


def detect_memory_opportunities() -> list[StrategicOpportunity]:
    snapshot = build_memory_snapshot()
    opportunities: list[StrategicOpportunity] = []

    for pattern in snapshot.patterns[:8]:
        opportunities.append(StrategicOpportunity(
            project_id=pattern.project_id,
            opportunity=pattern.pattern,
            domain="optimization",
            priority="high" if pattern.confidence >= 0.8 else "medium",
            confidence=pattern.confidence,
            evidence=pattern.evidence[:4],
        ))

    return opportunities


def detect_orchestrator_opportunities() -> list[StrategicOpportunity]:
    try:
        recommendations = orchestrator_recommendations().recommendations
    except Exception:
        return []

    return [
        StrategicOpportunity(
            project_id=item.project_id,
            opportunity=f"Portfolio orchestrator recommends {item.mission_id}",
            domain="automation",
            priority=_priority(item.optimization_score),
            confidence=round(item.optimization_score / 100, 2),
            evidence=item.reasons[:4],
        )
        for item in recommendations[:8]
    ]
