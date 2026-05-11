from app.memory_ai.heuristics import priority_from_confidence
from app.memory_ai.models import MemoryRecommendation


def recommendations_from_successes(successes: list) -> list[MemoryRecommendation]:
    recommendations: list[MemoryRecommendation] = []

    for success in successes:
        recommendations.append(MemoryRecommendation(
            project_id=success.project_id,
            mission_id=success.mission_id,
            recommendation="Repeat or schedule this mission pattern because historical outcomes are positive.",
            priority=priority_from_confidence(success.confidence),
            confidence=success.confidence,
            reasons=[
                f"success rate {success.success_rate}",
                f"{success.successes} successful signals",
            ],
        ))

    return recommendations


def recommendations_from_failures(failures: list) -> list[MemoryRecommendation]:
    recommendations: list[MemoryRecommendation] = []

    for failure in failures:
        recommendations.append(MemoryRecommendation(
            project_id=failure.project_id,
            mission_id=failure.mission_id,
            recommendation="Apply cooldown and review failed reports before retrying this mission.",
            priority="high" if failure.cooldown_recommended else "medium",
            confidence=min(1, failure.failure_rate),
            cooldown_recommended=failure.cooldown_recommended,
            retry_after_hours=failure.retry_after_hours,
            reasons=[
                f"failure rate {failure.failure_rate}",
                f"{failure.failures} failure signals",
            ],
        ))

    return recommendations


def build_adaptive_recommendations(successes: list, failures: list) -> list[MemoryRecommendation]:
    recommendations = recommendations_from_failures(failures) + recommendations_from_successes(successes)
    recommendations.sort(key=lambda item: (item.priority == "high", item.confidence), reverse=True)
    return recommendations
