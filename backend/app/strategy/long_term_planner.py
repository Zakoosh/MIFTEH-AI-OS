from app.intelligence.analyzer import analyze_projects, intelligence_project
from app.strategy.business_alignment import business_alignment
from app.strategy.growth_strategy import growth_strategy
from app.strategy.models import ProjectStrategy
from app.strategy.opportunity_detector import detect_project_opportunities
from app.strategy.roadmap_builder import build_30_day_roadmap, build_90_day_roadmap, roadmap_titles


def portfolio_role(project: object) -> str:
    if project.project_id == "mifteh-main-site":
        return "growth_and_conversion"
    if project.project_id == "mifteh":
        return "orchestration_platform"
    if project.project_id == "yallaplays":
        return "consumer_growth_engine"
    if project.project_id == "fionera":
        return "finance_intelligence_product"
    return "portfolio_project"


def build_project_strategy(project: object) -> ProjectStrategy:
    opportunities = detect_project_opportunities(project)
    roadmap_30 = build_30_day_roadmap(project, opportunities)
    roadmap_90 = build_90_day_roadmap(project, opportunities)
    growth = growth_strategy(project)

    return ProjectStrategy(
        project_id=project.project_id,
        project=project.name,
        project_type=project.project_type,
        strategy_focus=growth.focus,
        recommended_roadmap=roadmap_titles(roadmap_30[:3]),
        roadmap_30_day=roadmap_30,
        roadmap_90_day=roadmap_90,
        growth_strategy=growth,
        business_alignment=business_alignment(project),
        opportunities=opportunities,
        portfolio_role=portfolio_role(project),
        risks=project.warnings + project.priorities[:3],
    )


def build_project_strategies() -> list[ProjectStrategy]:
    return [build_project_strategy(project) for project in analyze_projects()]


def build_single_project_strategy(project_id: str) -> ProjectStrategy | None:
    project = intelligence_project(project_id)
    if project is None:
        return None

    return build_project_strategy(project)
