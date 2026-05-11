from app.strategy.models import GrowthStrategy


PROJECT_FOCUS = {
    "yallaplays": ["SEO growth", "game content expansion", "mobile UX", "monetization"],
    "fionera": ["finance intelligence", "security trust", "analytics workflows", "watchlists"],
    "mifteh": ["automation", "agent coordination", "mission intelligence", "operational analytics"],
    "mifteh-main-site": ["SEO growth", "lead generation", "branding", "conversion", "analytics"],
}


def _recommendations(project_id: str) -> list[str]:
    if project_id == "mifteh-main-site":
        return [
            "Improve landing pages and conversion paths",
            "Build analytics dashboards for acquisition and leads",
            "Create SEO content clusters around AI orchestration and automation",
        ]

    if project_id == "yallaplays":
        return [
            "Prioritize SEO pages for high-intent game categories",
            "Create new game content loops and internal links",
            "Improve mobile-first discovery and monetization surfaces",
        ]

    if project_id == "fionera":
        return [
            "Strengthen dashboard workflows for watchlists and portfolio insight",
            "Prioritize security posture and data trust",
            "Expand finance intelligence reports into product features",
        ]

    if project_id == "mifteh":
        return [
            "Improve orchestration visibility and automation controls",
            "Use memory patterns to improve mission selection",
            "Expand operational analytics in the command dashboard",
        ]

    return ["Prioritize growth, UX, automation, and scalable operations."]


def growth_strategy(project: object) -> GrowthStrategy:
    project_id = project.project_id
    focus = PROJECT_FOCUS.get(project_id, ["growth", "SEO", "automation", "scalability"])

    return GrowthStrategy(
        project_id=project_id,
        focus=focus,
        recommendations=_recommendations(project_id),
        monetization_paths=[
            "Improve conversion instrumentation",
            "Identify high-intent user journeys",
            "Turn repeated successful missions into growth workflows",
        ],
        seo_strategy=[
            "Track organic opportunities from mission recommendations",
            "Build content clusters around highest-value project themes",
            "Review metadata and structured data during each improvement cycle",
        ],
        branding_strategy=[
            "Clarify project positioning and trust signals",
            "Align dashboard insights with business-facing narratives",
            "Use analytics feedback to refine messaging",
        ],
    )
