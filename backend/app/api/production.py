from fastapi import APIRouter, Query

from app.production.fionera.analytics_pipeline import build_analytics_pipeline
from app.production.mifteh.branding_insights import branding_insights
from app.production.mifteh.landing_optimizer import landing_recommendations
from app.production.mifteh.lead_optimizer import lead_generation_recommendations
from app.production.mifteh.seo_cluster_builder import build_seo_clusters
from app.production.models import (
    FioneraProductionPlan,
    MiftehProductionPlan,
    MODE_APPLY_READY,
    MODE_PROPOSAL_ONLY,
    ProductionOverview,
    ProductionSafety,
    YallaPlaysProductionPlan,
)
from app.production.yallaplays.content_pipeline import build_content_pipeline
from app.strategy.engine import strategy_overview
from app.executive.engine import executive_overview


router = APIRouter(prefix="/production", tags=["production"])


def _safety(project_id: str, mode: str, implementation_allowed: bool) -> ProductionSafety:
    return ProductionSafety(
        project_id=project_id,
        mode=mode,
        implementation_allowed=implementation_allowed,
        destructive_operations_allowed=False,
        deployment_allowed=False,
        notes=[
            "No destructive operations",
            "No automatic deployment",
            "Preview-oriented workflow",
            "Apply only approved safe changes",
        ],
    )


def build_yallaplays_plan(limit: int = 5) -> YallaPlaysProductionPlan:
    pipeline = build_content_pipeline(limit=limit)
    return YallaPlaysProductionPlan(
        safety=_safety("yallaplays", MODE_APPLY_READY, True),
        games=pipeline["games"],
        seo=pipeline["seo"],
        categories=pipeline["categories"],
        mobile_ux=pipeline["mobile_ux"],
        content_pipeline=pipeline["pipeline"],
    )


def build_fionera_plan() -> FioneraProductionPlan:
    pipeline = build_analytics_pipeline()
    return FioneraProductionPlan(
        safety=_safety("fionera", MODE_APPLY_READY, True),
        market_signals=pipeline["market_signals"],
        insights=pipeline["insights"],
        watchlists=pipeline["watchlists"],
        ux_recommendations=pipeline["ux_recommendations"],
        analytics=pipeline["analytics"],
    )


def build_mifteh_plan() -> MiftehProductionPlan:
    return MiftehProductionPlan(
        safety=_safety("mifteh-main-site", MODE_PROPOSAL_ONLY, False),
        landing=landing_recommendations(),
        seo_clusters=build_seo_clusters(),
        branding=branding_insights(),
        lead_generation=lead_generation_recommendations(),
    )


@router.get("/yallaplays/games")
def production_yallaplays_games(limit: int = Query(default=5, ge=1, le=25)):
    return build_yallaplays_plan(limit=limit).model_dump()


@router.get("/yallaplays/seo")
def production_yallaplays_seo():
    plan = build_yallaplays_plan()
    return {
        "project_id": plan.project_id,
        "safety": plan.safety.model_dump(),
        "seo": plan.seo,
        "metadata": [game.metadata for game in plan.games],
        "categories": plan.categories,
    }


@router.get("/fionera/insights")
def production_fionera_insights():
    return build_fionera_plan().model_dump()


@router.get("/mifteh/recommendations")
def production_mifteh_recommendations():
    return build_mifteh_plan().model_dump()


@router.get("/overview")
def production_overview():
    try:
        strategy = strategy_overview()
        executive = executive_overview()
        highlights = [
            strategy.recommended_next_strategy,
            f"Executive focus: {executive.company_focus}",
            f"Priority project: {executive.highest_priority_project}",
        ]
    except Exception as exc:
        highlights = [f"Strategic context unavailable: {exc}"]

    return ProductionOverview(
        projects=["yallaplays", "fionera", "mifteh-main-site"],
        implementation_allowed={
            "yallaplays": True,
            "fionera": True,
            "mifteh-main-site": False,
        },
        proposal_only=["mifteh-main-site"],
        highlights=highlights,
    ).model_dump()
