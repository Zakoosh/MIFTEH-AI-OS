import json
from pathlib import Path

from app.orchestrator.models import OrchestrationCycle, OrchestratorTelemetry


ORCHESTRATOR_DIR = Path("/workspace/backend/app/memory/orchestrator")
CYCLES_FILE = ORCHESTRATOR_DIR / "cycles.json"


def _read_json_list(path: Path) -> list[dict]:
    if not path.is_file():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    return data if isinstance(data, list) else []


def _write_json_list(path: Path, data: list[dict]) -> None:
    ORCHESTRATOR_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def load_cycles() -> list[OrchestrationCycle]:
    cycles: list[OrchestrationCycle] = []

    for item in _read_json_list(CYCLES_FILE):
        try:
            cycles.append(OrchestrationCycle.model_validate(item))
        except Exception:
            continue

    cycles.sort(key=lambda cycle: cycle.started_at or "", reverse=True)
    return cycles


def save_cycle(cycle: OrchestrationCycle) -> None:
    cycles = load_cycles()
    cycles.insert(0, cycle)
    _write_json_list(CYCLES_FILE, [item.model_dump() for item in cycles[:100]])


def build_telemetry(cycles: list[OrchestrationCycle] | None = None) -> OrchestratorTelemetry:
    cycles = cycles if cycles is not None else load_cycles()
    by_project: dict[str, int] = {}
    by_area: dict[str, int] = {}
    scores: list[int] = []
    blocked_total = 0
    recommendations_total = 0

    for cycle in cycles:
        blocked_total += cycle.blocked_count
        recommendations_total += cycle.recommendations_count

        for recommendation in cycle.selected_recommendations:
            by_project[recommendation.project_id] = by_project.get(recommendation.project_id, 0) + 1
            scores.append(recommendation.optimization_score)

            for area in recommendation.improvement_areas:
                by_area[area] = by_area.get(area, 0) + 1

    latest = cycles[0] if cycles else None

    return OrchestratorTelemetry(
        cycles_total=len(cycles),
        recommendations_total=recommendations_total,
        blocked_total=blocked_total,
        average_optimization_score=round(sum(scores) / len(scores)) if scores else 0,
        last_cycle_id=latest.cycle_id if latest else None,
        last_cycle_at=latest.completed_at if latest else None,
        by_project=by_project,
        by_area=by_area,
    )
