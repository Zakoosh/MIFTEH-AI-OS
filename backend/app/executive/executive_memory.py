from app.executive.models import ExecutiveMemorySignal


def build_memory_signals(memory_snapshot: object) -> list[ExecutiveMemorySignal]:
    signals: list[ExecutiveMemorySignal] = []

    for pattern in getattr(memory_snapshot, "patterns", [])[:6]:
        signals.append(ExecutiveMemorySignal(
            signal=pattern.pattern,
            project_id=pattern.project_id,
            confidence=pattern.confidence,
            recommendation=(
                "Increase focus" if pattern.pattern_type == "success"
                else "Apply review and cooldown before retry"
            ),
        ))

    for recommendation in getattr(memory_snapshot, "recommendations", [])[:6]:
        signals.append(ExecutiveMemorySignal(
            signal=recommendation.recommendation,
            project_id=recommendation.project_id,
            confidence=recommendation.confidence,
            recommendation=(
                "Cooldown recommended" if recommendation.cooldown_recommended
                else "Use as prioritization signal"
            ),
        ))

    signals.sort(key=lambda item: item.confidence, reverse=True)
    return signals[:10]
