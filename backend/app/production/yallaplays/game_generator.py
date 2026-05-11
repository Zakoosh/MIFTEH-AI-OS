from app.production.models import YallaPlaysGameIdea
from app.strategy.engine import strategy_project


def generate_game_ideas(limit: int = 5) -> list[YallaPlaysGameIdea]:
    strategy = strategy_project("yallaplays")
    focus = "SEO growth" if strategy and "SEO growth" in strategy.strategy_focus else "game discovery"
    ideas = [
        ("Cyber Drift Racing", "Racing", "Racing", 82),
        ("Jungle Gem Runner", "Arcade", "Adventure", 86),
        ("Space Merge Defense", "Strategy", "Puzzle", 79),
        ("Penalty Star Challenge", "Sports", "Sports", 84),
        ("Neon Bubble Quest", "Puzzle", "Puzzle", 88),
    ]

    return [
        YallaPlaysGameIdea(
            game_idea=name,
            genre=genre,
            category=category,
            seo_title=f"Play {name} Online Free",
            mobile_score=mobile_score,
            implementation_tasks=[
                "Create game detail page preview",
                "Generate SEO metadata and internal links",
                "Prepare mobile-first controls checklist",
                f"Align launch copy with {focus}",
            ],
            metadata={
                "slug": name.lower().replace(" ", "-"),
                "description": f"Play {name} free on YallaPlays with fast mobile-friendly gameplay.",
                "keywords": [category.lower(), genre.lower(), "free online game", "html5 game"],
            },
        )
        for name, genre, category, mobile_score in ideas[:limit]
    ]
