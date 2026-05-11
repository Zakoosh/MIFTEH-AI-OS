from app.strategy.long_term_planner import build_project_strategies, build_single_project_strategy
from app.strategy.models import (
    OpportunityCollection,
    ProjectStrategyCollection,
    RoadmapCollection,
    StrategyOverview,
)
from app.strategy.portfolio_strategy import build_portfolio_strategy


def strategy_projects() -> ProjectStrategyCollection:
    return ProjectStrategyCollection(projects=build_project_strategies())


def strategy_project(project_id: str):
    return build_single_project_strategy(project_id)


def strategy_roadmaps() -> RoadmapCollection:
    projects = build_project_strategies()
    roadmap_30 = []
    roadmap_90 = []

    for project in projects:
        roadmap_30.extend(project.roadmap_30_day)
        roadmap_90.extend(project.roadmap_90_day)

    return RoadmapCollection(roadmap_30_day=roadmap_30, roadmap_90_day=roadmap_90)


def strategy_opportunities() -> OpportunityCollection:
    projects = build_project_strategies()
    portfolio = build_portfolio_strategy(projects)
    opportunities = portfolio.cross_project_opportunities.copy()

    for project in projects:
        opportunities.extend(project.opportunities)

    opportunities.sort(key=lambda item: (item.priority == "high", item.confidence), reverse=True)
    return OpportunityCollection(opportunities=opportunities)


def strategy_overview() -> StrategyOverview:
    projects = build_project_strategies()
    portfolio = build_portfolio_strategy(projects)
    opportunities = strategy_opportunities().opportunities
    highest = max(projects, key=lambda item: item.business_alignment.alignment_score, default=None)

    return StrategyOverview(
        portfolio_focus=portfolio.strategic_priorities,
        highest_priority_project=highest.project_id if highest else "",
        recommended_next_strategy=opportunities[0].opportunity if opportunities else "",
        opportunities_count=len(opportunities),
        projects_count=len(projects),
        portfolio=portfolio,
        projects=projects,
    )
