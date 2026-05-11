from app.memory_ai.models import AdaptiveHeuristic


DEFAULT_HEURISTICS = [
    AdaptiveHeuristic(
        name="repeat_successful_missions",
        description="Missions with repeated successful reports should be recommended more often.",
        weight=1.2,
        applies_to=["success_memory", "mission_effectiveness"],
    ),
    AdaptiveHeuristic(
        name="cooldown_repeated_failures",
        description="Missions with repeated failures should receive cooldown recommendations before retry.",
        weight=1.4,
        applies_to=["failure_memory", "cooldowns"],
    ),
    AdaptiveHeuristic(
        name="boost_continuous_improvement_domains",
        description="SEO, UI/UX, performance, branding, analytics, conversion, automation, and scalability remain ongoing priorities.",
        weight=1.1,
        applies_to=["optimization_memory", "orchestration"],
    ),
    AdaptiveHeuristic(
        name="prefer_high_confidence_patterns",
        description="Patterns with stronger historical evidence should improve future recommendation confidence.",
        weight=1.3,
        applies_to=["pattern_detection", "decision_support"],
    ),
]


def list_heuristics() -> list[AdaptiveHeuristic]:
    return DEFAULT_HEURISTICS.copy()


def confidence_from_rate(rate: float, observations: int) -> float:
    volume_weight = min(observations / 5, 1)
    return round(max(0, min(1, rate * 0.7 + volume_weight * 0.3)), 2)


def recommended_frequency(confidence: float) -> str:
    if confidence >= 0.85:
        return "daily"
    if confidence >= 0.65:
        return "twice_weekly"
    if confidence >= 0.4:
        return "weekly"
    return "monitor"


def priority_from_confidence(confidence: float) -> str:
    if confidence >= 0.85:
        return "high"
    if confidence >= 0.55:
        return "medium"
    return "low"
