from app.strategy.models import RoadmapItem
from app.strategy.optimization_strategy import optimization_items


def build_30_day_roadmap(project: object, opportunities: list) -> list[RoadmapItem]:
    items = [
        RoadmapItem(
            project_id=project.project_id,
            horizon="30_day",
            title=opportunity.opportunity,
            focus=opportunity.domain,
            priority=opportunity.priority,
            expected_outcome="Convert near-term signal into measurable improvement",
            source="opportunity",
        )
        for opportunity in opportunities[:3]
    ]
    items.extend(item for item in optimization_items(project) if item.horizon == "30_day")
    return items[:6]


def build_90_day_roadmap(project: object, opportunities: list) -> list[RoadmapItem]:
    items = [
        RoadmapItem(
            project_id=project.project_id,
            horizon="90_day",
            title=f"Scale {opportunity.domain} program for {project.name}",
            focus=opportunity.domain,
            priority=opportunity.priority,
            expected_outcome="Build repeatable portfolio-level growth capability",
            source="opportunity",
        )
        for opportunity in opportunities[:4]
    ]
    items.extend(item for item in optimization_items(project) if item.horizon == "90_day")
    return items[:6]


def roadmap_titles(items: list[RoadmapItem]) -> list[str]:
    return [item.title for item in items]
