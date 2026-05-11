def build_metadata(game_ideas: list) -> list[dict]:
    metadata = []
    for game in game_ideas:
        metadata.append({
            "slug": game.metadata.get("slug"),
            "title": game.seo_title,
            "category": game.category,
            "schema_type": "VideoGame",
            "og_title": game.seo_title,
            "og_description": game.metadata.get("description"),
            "implementation_ready": True,
        })
    return metadata
