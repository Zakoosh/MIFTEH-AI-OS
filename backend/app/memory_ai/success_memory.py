from app.memory_ai.heuristics import confidence_from_rate
from app.memory_ai.models import SuccessMemory


def build_success_memory(effectiveness: dict[str, dict]) -> list[SuccessMemory]:
    successes: list[SuccessMemory] = []

    for item in effectiveness.values():
        observations = item["successes"] + item["failures"]
        if observations <= 0 or item["successes"] <= 0:
            continue

        success_rate = item["successes"] / observations
        if success_rate < 0.5:
            continue

        successes.append(SuccessMemory(
            project_id=item["project_id"],
            mission_id=item["mission_id"],
            successes=item["successes"],
            success_rate=round(success_rate, 2),
            confidence=confidence_from_rate(success_rate, observations),
            effective_sequence=[
                item["mission_id"],
                "review-reports",
                "schedule-next-optimization",
            ],
            evidence=item["evidence"][:8],
        ))

    successes.sort(key=lambda memory: (memory.confidence, memory.successes), reverse=True)
    return successes
