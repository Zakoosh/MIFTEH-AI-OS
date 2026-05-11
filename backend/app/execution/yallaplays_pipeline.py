from app.execution.models import ExecutionPreview
from app.production.yallaplays.category_optimizer import optimize_categories
from app.production.yallaplays.content_pipeline import build_content_pipeline
from app.production.yallaplays.mobile_optimizer import mobile_ux_recommendations
from app.production.yallaplays.seo_generator import generate_seo_plan


def run_yallaplays_game_batch(limit: int = 5) -> ExecutionPreview:
    pipeline = build_content_pipeline(limit=limit)
    items = []
    for game in pipeline["games"]:
        items.append({
            "type": "game",
            "title": game["game_idea"],
            "category": game["category"],
            "seo_title": game["seo_title"],
            "mobile_score": game["mobile_score"],
            "implementation_ready": True,
            "deployment_allowed": False,
            "destructive": False,
        })

    return ExecutionPreview(
        pipeline="yallaplays_game_batch",
        project_id="yallaplays",
        summary=f"Generated {len(items)} implementation-ready game previews",
        items=items,
    )


def run_yallaplays_seo_batch(limit: int = 25) -> ExecutionPreview:
    seo_items = generate_seo_plan()
    category_items = optimize_categories()
    items = [
        {
            "type": "seo_metadata",
            "page": item["page"],
            "seo_title": item["seo_title"],
            "priority": item["priority"],
            "implementation_ready": True,
            "deployment_allowed": False,
            "destructive": False,
        }
        for item in seo_items
    ] + [
        {
            "type": "category_optimization",
            "category": item["category"],
            "action": item["action"],
            "seo_value": item["seo_value"],
            "implementation_ready": True,
            "deployment_allowed": False,
            "destructive": False,
        }
        for item in category_items
    ]

    return ExecutionPreview(
        pipeline="yallaplays_seo_batch",
        project_id="yallaplays",
        summary=f"Generated {len(items[:limit])} SEO/category optimization previews",
        items=items[:limit],
    )


def run_yallaplays_mobile_cycle() -> ExecutionPreview:
    items = [
        {
            "type": "mobile_optimization",
            **item,
            "deployment_allowed": False,
            "destructive": False,
        }
        for item in mobile_ux_recommendations()
    ]

    return ExecutionPreview(
        pipeline="yallaplays_mobile_cycle",
        project_id="yallaplays",
        summary=f"Generated {len(items)} mobile optimization previews",
        items=items,
    )
