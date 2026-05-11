from app.strategy.models import PortfolioStrategy, StrategicOpportunity
from app.strategy.opportunity_detector import detect_memory_opportunities, detect_orchestrator_opportunities


def build_cross_project_opportunities(project_strategies: list) -> list[StrategicOpportunity]:
    opportunities = detect_memory_opportunities() + detect_orchestrator_opportunities()

    opportunities.append(StrategicOpportunity(
        project_id="portfolio",
        opportunity="Coordinate analytics and conversion dashboards across all connected projects",
        domain="analytics",
        priority="high",
        confidence=0.78,
        evidence=["dashboard", "memory_ai", "strategy"],
    ))
    opportunities.append(StrategicOpportunity(
        project_id="portfolio",
        opportunity="Use MIFTEH Main Site as the brand and lead-generation layer for the broader AI OS portfolio",
        domain="branding",
        priority="high",
        confidence=0.82,
        evidence=["mifteh-main-site", "business-platform"],
    ))

    opportunities.sort(key=lambda item: (item.priority == "high", item.confidence), reverse=True)
    return opportunities[:12]


def build_portfolio_strategy(project_strategies: list) -> PortfolioStrategy:
    opportunities = build_cross_project_opportunities(project_strategies)
    risks: list[str] = []

    for strategy in project_strategies:
        if strategy.business_alignment.alignment_score < 60:
            risks.append(f"{strategy.project_id} needs stronger business alignment")
        if strategy.risks:
            risks.append(f"{strategy.project_id}: {strategy.risks[0]}")

    return PortfolioStrategy(
        projects_count=len(project_strategies),
        strategic_priorities=[
            "Grow MIFTEH Main Site as the business-facing acquisition layer",
            "Use memory patterns to improve mission selection and cooldowns",
            "Convert repeated optimization wins into scheduled workflows",
            "Improve operational analytics visibility in the dashboard",
        ],
        cross_project_opportunities=opportunities,
        portfolio_risks=risks[:8],
        coordination_plan=[
            "Align SEO and branding missions across main site and product projects",
            "Route high-confidence memory patterns into decision prioritization",
            "Review failed mission clusters before scheduling new automation",
            "Use portfolio dashboard metrics to tune monthly roadmaps",
        ],
    )
