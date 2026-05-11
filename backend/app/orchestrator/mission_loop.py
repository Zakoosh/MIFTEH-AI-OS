from app.decision.engine import decision_recommendations
from app.orchestrator.cooldowns import cooldown_constraint
from app.orchestrator.execution_policy import scheduler_action
from app.orchestrator.models import OrchestratorRecommendation
from app.orchestrator.optimization_engine import continuous_areas, optimization_score
from app.orchestrator.safeguards import (
    convert_decision_constraints,
    dashboard_continuous_improvement_constraint,
    has_blocking_constraint,
    repeated_failure_constraint,
)


def build_recommendation_loop(
    previous_cycles: list,
    include_blocked: bool = False,
) -> list[OrchestratorRecommendation]:
    recommendations: list[OrchestratorRecommendation] = []

    try:
        decisions = decision_recommendations().recommendations
    except Exception:
        return []

    for decision in decisions:
        constraints = convert_decision_constraints(decision)
        constraints.append(repeated_failure_constraint(decision))
        constraints.append(dashboard_continuous_improvement_constraint(decision))
        constraints.append(cooldown_constraint(
            project_id=decision.project_id,
            mission_id=decision.mission_id,
            cycles=previous_cycles,
        ))

        blocked = decision.blocked or has_blocking_constraint(constraints)
        if blocked and not include_blocked:
            continue

        score = optimization_score(decision)
        areas = continuous_areas(decision)

        recommendations.append(OrchestratorRecommendation(
            project_id=decision.project_id,
            project=decision.project,
            mission_id=decision.mission_id,
            title=decision.title,
            priority=decision.priority,
            optimization_score=score,
            decision_score=decision.decision_score,
            urgency_score=decision.urgency_score,
            impact_score=decision.impact_score,
            automation_readiness=decision.automation_readiness,
            recommended_agents=decision.recommended_agents,
            improvement_areas=areas,
            constraints=constraints,
            scheduler_action=scheduler_action(
                optimization_score=score,
                automation_readiness=decision.automation_readiness,
                blocked=blocked,
            ),
            blocked=blocked,
            reasons=decision.reasons,
        ))

    recommendations.sort(key=lambda item: item.optimization_score, reverse=True)
    return recommendations
