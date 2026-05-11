from app.strategy.models import RoadmapItem


def optimization_items(project: object) -> list[RoadmapItem]:
    items: list[RoadmapItem] = []

    if project.health.overall_health < 70:
        items.append(RoadmapItem(
            project_id=project.project_id,
            horizon="30_day",
            title="Stabilize project health score",
            focus="operational health",
            priority="high",
            expected_outcome="Raise confidence for follow-on growth work",
        ))

    if project.health.automation_readiness < 70:
        items.append(RoadmapItem(
            project_id=project.project_id,
            horizon="30_day",
            title="Improve automation readiness",
            focus="automation",
            priority="medium",
            expected_outcome="Prepare recurring missions for safe scheduling",
        ))

    if project.trend.neglected:
        items.append(RoadmapItem(
            project_id=project.project_id,
            horizon="30_day",
            title="Restart continuous improvement cadence",
            focus="operational analytics",
            priority="high",
            expected_outcome="Recover recent activity and improve learning signals",
        ))

    items.append(RoadmapItem(
        project_id=project.project_id,
        horizon="90_day",
        title="Turn repeated learnings into strategic operating loops",
        focus="scalability",
        priority="medium",
        expected_outcome="Build durable cross-cycle optimization practices",
    ))

    return items
