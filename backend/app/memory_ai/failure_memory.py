from app.memory_ai.models import FailureMemory


def _retry_after_hours(failure_rate: float, failures: int) -> int:
    if failure_rate >= 0.8 or failures >= 3:
        return 12

    if failure_rate >= 0.5:
        return 6

    return 0


def build_failure_memory(effectiveness: dict[str, dict]) -> list[FailureMemory]:
    failures: list[FailureMemory] = []

    for item in effectiveness.values():
        observations = item["successes"] + item["failures"]
        if observations <= 0 or item["failures"] <= 0:
            continue

        failure_rate = item["failures"] / observations
        if failure_rate < 0.35:
            continue

        retry_after_hours = _retry_after_hours(failure_rate, item["failures"])
        failures.append(FailureMemory(
            project_id=item["project_id"],
            mission_id=item["mission_id"],
            failures=item["failures"],
            failure_rate=round(failure_rate, 2),
            cooldown_recommended=retry_after_hours > 0,
            retry_after_hours=retry_after_hours,
            evidence=item["evidence"][:8],
        ))

    failures.sort(key=lambda memory: (memory.cooldown_recommended, memory.failure_rate, memory.failures), reverse=True)
    return failures
