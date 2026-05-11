from app.strategy.models import BusinessAlignment


BUSINESS_GOALS = {
    "yallaplays": "Grow organic game traffic, increase engagement, improve monetization, and expand game content.",
    "fionera": "Improve finance intelligence, investor workflows, analytics quality, and trust/security.",
    "mifteh": "Improve AI orchestration, automation, memory, mission intelligence, and dashboard operations.",
    "mifteh-main-site": "Grow brand visibility, convert visitors into leads, improve analytics, and scale business platform operations.",
}


def _alignment_notes(project: object) -> list[str]:
    notes: list[str] = []

    if project.health.overall_health < 60:
        notes.append("Improve operational health before scaling strategic initiatives.")

    if project.health.automation_readiness >= 70:
        notes.append("Project is ready for more scheduled optimization workflows.")
    else:
        notes.append("Automation readiness should improve before heavier orchestration.")

    if project.recommendations:
        notes.append(f"Top recommendation supports {project.recommendations[0].mission_id}.")

    if project.trend.neglected:
        notes.append("Recent activity is low; add near-term roadmap momentum.")

    return notes


def business_alignment(project: object) -> BusinessAlignment:
    base_score = round((project.health.overall_health + project.health.automation_readiness) / 2)
    if project.recommendations:
        base_score += min(project.recommendations[0].score // 10, 10)

    return BusinessAlignment(
        project_id=project.project_id,
        business_goal=BUSINESS_GOALS.get(project.project_id, "Continuously improve project growth, quality, and scalability."),
        alignment_score=max(0, min(100, base_score)),
        alignment_notes=_alignment_notes(project),
    )
