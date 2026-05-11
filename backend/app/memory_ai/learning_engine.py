import json

from app.memory_ai.adaptive_rules import build_adaptive_recommendations
from app.memory_ai.failure_memory import build_failure_memory
from app.memory_ai.heuristics import list_heuristics
from app.memory_ai.models import AdaptiveMemorySnapshot
from app.memory_ai.optimization_memory import collect_memory_sources, summarize_mission_effectiveness
from app.memory_ai.pattern_detector import detect_patterns
from app.memory_ai.retention import SNAPSHOT_FILE, ensure_memory_dir, trim_items
from app.memory_ai.success_memory import build_success_memory


def build_memory_snapshot(persist: bool = False) -> AdaptiveMemorySnapshot:
    sources = collect_memory_sources()
    effectiveness = summarize_mission_effectiveness(sources)
    successes = trim_items(build_success_memory(effectiveness))
    failures = trim_items(build_failure_memory(effectiveness))
    patterns = trim_items(detect_patterns(successes, failures, effectiveness))
    recommendations = trim_items(build_adaptive_recommendations(successes, failures))
    heuristics = list_heuristics()

    snapshot = AdaptiveMemorySnapshot(
        generated_at=sources["generated_at"],
        projects_count=len(sources.get("intelligence_projects", [])),
        patterns=patterns,
        successes=successes,
        failures=failures,
        recommendations=recommendations,
        heuristics=heuristics,
    )

    if persist:
        ensure_memory_dir()
        SNAPSHOT_FILE.write_text(
            json.dumps(snapshot.model_dump(), indent=2, ensure_ascii=False, default=str),
            encoding="utf-8",
        )

    return snapshot


def memory_patterns():
    return build_memory_snapshot().patterns


def memory_successes():
    return build_memory_snapshot().successes


def memory_failures():
    return build_memory_snapshot().failures


def memory_recommendations():
    return build_memory_snapshot().recommendations


def memory_heuristics():
    return build_memory_snapshot().heuristics
