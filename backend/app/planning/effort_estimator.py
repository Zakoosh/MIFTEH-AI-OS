"""
effort_estimator.py — Detailed effort estimation with complexity and risk buffers.
"""

from __future__ import annotations

from typing import Any

from .models import EffortEstimate, CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW


# Complexity multiplier per task type (accounts for cross-team coordination,
# hidden integration work, and domain complexity).
_COMPLEXITY: dict[str, float] = {
    "implementation": 1.30,
    "feature":        1.25,
    "analytics":      1.20,
    "monetization":   1.20,
    "watchlist":      1.10,
    "widget":         1.05,
    "dashboard":      1.10,
    "seo_campaign":   1.00,
    "ux":             1.05,
    "campaign":       1.00,
    "optimization":   1.00,
    "content":        0.90,
    "roadmap":        0.85,
}

# Risk buffer percentage per priority level
_RISK_BUFFER: dict[str, float] = {
    "critical": 25.0,
    "high":     20.0,
    "medium":   15.0,
    "low":      10.0,
}

# Phase breakdown: what fraction of total adjusted days goes to each phase
_PHASE_SPLIT: dict[str, dict[str, float]] = {
    "feature": {
        "preparation":   0.15,
        "implementation":0.50,
        "review":        0.20,
        "deployment":    0.10,
        "validation":    0.05,
    },
    "implementation": {
        "preparation":   0.20,
        "implementation":0.45,
        "review":        0.20,
        "deployment":    0.10,
        "validation":    0.05,
    },
    "seo_campaign": {
        "preparation":   0.20,
        "implementation":0.45,
        "review":        0.10,
        "deployment":    0.15,
        "validation":    0.10,
    },
    "ux": {
        "preparation":   0.30,
        "implementation":0.40,
        "review":        0.15,
        "deployment":    0.05,
        "validation":    0.10,
    },
    "dashboard": {
        "preparation":   0.15,
        "implementation":0.50,
        "review":        0.20,
        "deployment":    0.10,
        "validation":    0.05,
    },
}

_DEFAULT_SPLIT = {
    "preparation":    0.15,
    "implementation": 0.50,
    "review":         0.20,
    "deployment":     0.10,
    "validation":     0.05,
}

# Confidence level — lower raw days + higher complexity = lower confidence
def _confidence(raw_days: int, complexity: float, priority: str) -> str:
    if raw_days <= 7 and complexity <= 1.10:
        return CONFIDENCE_HIGH
    if raw_days >= 20 or complexity >= 1.25 or priority == "critical":
        return CONFIDENCE_LOW
    return CONFIDENCE_MEDIUM


def estimate(item: Any) -> EffortEstimate:
    complexity   = _COMPLEXITY.get(item.task_type, 1.10)
    buffer_pct   = _RISK_BUFFER.get(item.priority, 15.0)
    raw          = item.estimated_days

    adjusted     = raw * complexity
    buffer_days  = adjusted * (buffer_pct / 100.0)
    total        = adjusted + buffer_days

    split        = _PHASE_SPLIT.get(item.task_type, _DEFAULT_SPLIT)
    breakdown    = {phase: round(total * frac, 1) for phase, frac in split.items()}

    confidence   = _confidence(raw, complexity, item.priority)

    return EffortEstimate(
        estimate_id          = f"est_{item.item_id}",
        work_item_id         = item.item_id,
        project              = item.project,
        task_type            = item.task_type,
        title                = item.title,
        raw_effort_days      = raw,
        complexity_factor    = round(complexity, 2),
        risk_buffer_pct      = buffer_pct,
        adjusted_effort_days = round(adjusted, 1),
        risk_buffer_days     = round(buffer_days, 1),
        total_days           = round(total, 1),
        breakdown            = breakdown,
        confidence           = confidence,
    )


def estimate_all(items: list[Any]) -> list[EffortEstimate]:
    return [estimate(i) for i in items]


def total_effort_days(items: list[Any]) -> float:
    return round(sum(estimate(i).total_days for i in items), 1)
