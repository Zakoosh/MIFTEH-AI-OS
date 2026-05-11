from app.memory_ai.heuristics import recommended_frequency
from app.memory_ai.models import MemoryPattern


def detect_success_patterns(successes: list) -> list[MemoryPattern]:
    patterns: list[MemoryPattern] = []

    for success in successes:
        patterns.append(MemoryPattern(
            pattern=f"{success.mission_id} missions improve {success.project_id} optimization confidence",
            project_id=success.project_id,
            mission_id=success.mission_id,
            pattern_type="success",
            confidence=success.confidence,
            recommended_frequency=recommended_frequency(success.confidence),
            evidence=success.evidence,
        ))

    return patterns


def detect_failure_patterns(failures: list) -> list[MemoryPattern]:
    patterns: list[MemoryPattern] = []

    for failure in failures:
        confidence = min(1, failure.failure_rate)
        patterns.append(MemoryPattern(
            pattern=f"{failure.mission_id} repeatedly fails on {failure.project_id}",
            project_id=failure.project_id,
            mission_id=failure.mission_id,
            pattern_type="failure",
            confidence=round(confidence, 2),
            recommended_frequency="cooldown",
            evidence=failure.evidence,
        ))

    return patterns


def detect_sequence_patterns(effectiveness: dict[str, dict]) -> list[MemoryPattern]:
    patterns: list[MemoryPattern] = []

    for item in effectiveness.values():
        if item["orchestration_recommendations"] <= 0:
            continue

        observations = item["successes"] + item["failures"]
        if observations <= 0:
            continue

        confidence = round((item["successes"] / observations) * 0.7 + 0.2, 2)
        patterns.append(MemoryPattern(
            pattern=f"orchestrator repeatedly selects {item['mission_id']} for {item['project_id']}",
            project_id=item["project_id"],
            mission_id=item["mission_id"],
            pattern_type="sequence",
            confidence=min(confidence, 1),
            recommended_frequency=recommended_frequency(confidence),
            evidence=item["evidence"][:8],
        ))

    return patterns


def detect_patterns(successes: list, failures: list, effectiveness: dict[str, dict]) -> list[MemoryPattern]:
    patterns = (
        detect_success_patterns(successes)
        + detect_failure_patterns(failures)
        + detect_sequence_patterns(effectiveness)
    )
    patterns.sort(key=lambda pattern: pattern.confidence, reverse=True)
    return patterns
