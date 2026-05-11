from app.production.yallaplays.category_optimizer import optimize_categories
from app.production.yallaplays.game_generator import generate_game_ideas
from app.production.yallaplays.metadata_builder import build_metadata
from app.production.yallaplays.mobile_optimizer import mobile_ux_recommendations
from app.production.yallaplays.seo_generator import generate_seo_plan


def build_content_pipeline(limit: int = 5) -> dict:
    games = generate_game_ideas(limit=limit)
    return {
        "games": [game.model_dump() for game in games],
        "metadata": build_metadata(games),
        "seo": generate_seo_plan(),
        "categories": optimize_categories(),
        "mobile_ux": mobile_ux_recommendations(),
        "pipeline": [
            "Generate game idea",
            "Build metadata and SEO plan",
            "Preview category placement",
            "Review mobile UX checklist",
            "Apply only approved non-destructive changes",
        ],
    }
