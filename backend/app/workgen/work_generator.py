"""
work_generator.py — Orchestrates work item generation for all projects.

Aggregates items from project-specific catalogs, seo_campaigns,
roadmap_expansion, and prioritization into unified batches.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import WorkItem, Campaign, RoadmapItem, WorkBatch, PriorityScore, WorkGenConfig
from .yallaplays_workgen import get_yallaplays_work_items
from .fionera_workgen import get_fionera_work_items
from .seo_campaigns import get_yallaplays_campaigns, get_fionera_campaigns
from .roadmap_expansion import get_yallaplays_roadmap, get_fionera_roadmap
from .prioritization import rank_items


class WorkGenerator:
    """Aggregates and filters work items across all projects."""

    def __init__(self, config: WorkGenConfig | None = None) -> None:
        self._config = config or WorkGenConfig()

    # ── Work items ────────────────────────────────────────────────────────

    def generate_yallaplays(
        self,
        task_types: list[str] | None = None,
        max_items: int = 20,
    ) -> list[WorkItem]:
        items = get_yallaplays_work_items()
        return self._filter_and_cap(items, task_types, max_items)

    def generate_fionera(
        self,
        task_types: list[str] | None = None,
        max_items: int = 20,
    ) -> list[WorkItem]:
        items = get_fionera_work_items()
        return self._filter_and_cap(items, task_types, max_items)

    def generate_all(
        self,
        task_types: list[str] | None = None,
        max_items: int = 20,
    ) -> dict[str, list[WorkItem]]:
        return {
            "yallaplays": self.generate_yallaplays(task_types, max_items),
            "fionera":    self.generate_fionera(task_types, max_items),
        }

    # ── Campaigns ─────────────────────────────────────────────────────────

    def get_campaigns(self, project: str = "all") -> list[Campaign]:
        campaigns: list[Campaign] = []
        if project in ("all", "yallaplays"):
            campaigns.extend(get_yallaplays_campaigns())
        if project in ("all", "fionera"):
            campaigns.extend(get_fionera_campaigns())
        return campaigns

    # ── Roadmap ───────────────────────────────────────────────────────────

    def get_roadmap(self, project: str = "all") -> list[RoadmapItem]:
        items: list[RoadmapItem] = []
        if project in ("all", "yallaplays"):
            items.extend(get_yallaplays_roadmap())
        if project in ("all", "fionera"):
            items.extend(get_fionera_roadmap())
        return items

    # ── Priorities ────────────────────────────────────────────────────────

    def get_priorities(self, project: str = "all") -> list[PriorityScore]:
        all_items: list[WorkItem] = []
        if project in ("all", "yallaplays"):
            all_items.extend(get_yallaplays_work_items())
        if project in ("all", "fionera"):
            all_items.extend(get_fionera_work_items())
        return rank_items(all_items)

    # ── Batch ─────────────────────────────────────────────────────────────

    def build_batch(self, project: str, batch_type: str = "full") -> WorkBatch:
        items = (
            self.generate_yallaplays() if project == "yallaplays"
            else self.generate_fionera()
        )
        campaigns = self.get_campaigns(project)
        roadmap   = self.get_roadmap(project)

        total_days = sum(i.estimated_days for i in items)
        avg_impact = (
            sum(i.estimated_impact for i in items) / len(items) if items else 0.0
        )

        return WorkBatch(
            project              = project,
            batch_type           = batch_type,
            title                = f"{project.title()} {batch_type.title()} Work Batch",
            work_item_ids        = [i.item_id for i in items],
            campaign_ids         = [c.campaign_id for c in campaigns],
            roadmap_ids          = [r.roadmap_id for r in roadmap],
            total_items          = len(items),
            total_estimated_days = total_days,
            avg_estimated_impact = round(avg_impact, 2),
            generated_at         = datetime.now().isoformat(),
            summary              = (
                f"{len(items)} work items, {len(campaigns)} campaigns, "
                f"{len(roadmap)} roadmap entries across {project}."
            ),
        )

    # ── Summary stats ─────────────────────────────────────────────────────

    def summary_stats(self, items: list[WorkItem]) -> dict[str, Any]:
        if not items:
            return {"total": 0}
        by_type: dict[str, int] = {}
        by_priority: dict[str, int] = {}
        for it in items:
            by_type[it.task_type] = by_type.get(it.task_type, 0) + 1
            by_priority[it.priority] = by_priority.get(it.priority, 0) + 1
        return {
            "total":              len(items),
            "by_task_type":       by_type,
            "by_priority":        by_priority,
            "total_estimated_days": sum(i.estimated_days for i in items),
            "avg_estimated_impact": round(
                sum(i.estimated_impact for i in items) / len(items), 2
            ),
        }

    # ── Internal ──────────────────────────────────────────────────────────

    @staticmethod
    def _filter_and_cap(
        items: list[WorkItem],
        task_types: list[str] | None,
        max_items: int,
    ) -> list[WorkItem]:
        if task_types:
            items = [i for i in items if i.task_type in task_types]
        return items[:max_items]


_instance: WorkGenerator | None = None


def get_generator() -> WorkGenerator:
    global _instance
    if _instance is None:
        _instance = WorkGenerator()
    return _instance
