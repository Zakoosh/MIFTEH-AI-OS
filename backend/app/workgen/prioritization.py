"""
prioritization.py — Composite priority scoring engine for work items.

Scores each WorkItem across four dimensions:
  - impact_score       (50% weight) — business/user impact
  - feasibility_score  (20% weight) — inversely proportional to effort
  - urgency_score      (20% weight) — derived from priority label and quarter
  - alignment_score    (10% weight) — strategic fit based on task type

Final composite_score = weighted sum, 0–100.
"""

from __future__ import annotations

from datetime import datetime

from .models import (
    WorkItem, PriorityScore,
    PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW,
    EFFORT_LOW, EFFORT_MEDIUM, EFFORT_HIGH,
)


_PRIORITY_URGENCY: dict[str, float] = {
    PRIORITY_CRITICAL: 100.0,
    PRIORITY_HIGH:     80.0,
    PRIORITY_MEDIUM:   55.0,
    PRIORITY_LOW:      30.0,
}

_EFFORT_FEASIBILITY: dict[str, float] = {
    EFFORT_LOW:    90.0,
    EFFORT_MEDIUM: 65.0,
    EFFORT_HIGH:   40.0,
}

_STRATEGIC_ALIGNMENT: dict[str, float] = {
    "seo_campaign":     90.0,
    "feature":          85.0,
    "implementation":   80.0,
    "roadmap":          75.0,
    "ux":               80.0,
    "dashboard":        85.0,
    "monetization":     95.0,
    "campaign":         88.0,
    "optimization":     82.0,
    "content":          78.0,
    "watchlist":        80.0,
    "widget":           83.0,
    "analytics":        82.0,
}

_IMPACT_W      = 0.50
_FEASIBILITY_W = 0.20
_URGENCY_W     = 0.20
_ALIGNMENT_W   = 0.10


def _score_to_priority(score: float) -> str:
    if score >= 88:
        return PRIORITY_CRITICAL
    if score >= 75:
        return PRIORITY_HIGH
    if score >= 55:
        return PRIORITY_MEDIUM
    return PRIORITY_LOW


def score_item(item: WorkItem) -> PriorityScore:
    impact      = float(item.estimated_impact)
    feasibility = _EFFORT_FEASIBILITY.get(item.estimated_effort, 65.0)
    urgency     = _PRIORITY_URGENCY.get(item.priority, 55.0)
    alignment   = _STRATEGIC_ALIGNMENT.get(item.task_type, 75.0)

    composite = (
        impact      * _IMPACT_W +
        feasibility * _FEASIBILITY_W +
        urgency     * _URGENCY_W +
        alignment   * _ALIGNMENT_W
    )

    return PriorityScore(
        item_id          = item.item_id,
        title            = item.title,
        project          = item.project,
        task_type        = item.task_type,
        composite_score  = round(composite, 2),
        impact_score     = round(impact, 2),
        feasibility_score= round(feasibility, 2),
        urgency_score    = round(urgency, 2),
        alignment_score  = round(alignment, 2),
        priority         = _score_to_priority(composite),
        computed_at      = datetime.now().isoformat(),
    )


def rank_items(items: list[WorkItem]) -> list[PriorityScore]:
    scores = [score_item(item) for item in items]
    scores.sort(key=lambda s: s.composite_score, reverse=True)
    for i, s in enumerate(scores, start=1):
        s.rank = i
    return scores
