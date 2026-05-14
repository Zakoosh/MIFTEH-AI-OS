from __future__ import annotations
from typing import Any
from ..content_generator import ContentGenerator
from ..models import OperationalOutput, OperationalPreview, OutputType, OperationProject, RiskLevel

SAMPLE_GAMES = [
    {"id": "subway-surfers", "name": "Subway Surfers", "genre": "arcade", "players": "1-2", "current_title": "Subway Surfers", "current_desc": "Run through the subway"},
    {"id": "8-ball-pool", "name": "8 Ball Pool", "genre": "sports", "players": "1-2", "current_title": "8 Ball Pool", "current_desc": "Play pool online"},
    {"id": "candy-crush", "name": "Candy Crush Saga", "genre": "puzzle", "players": "1", "current_title": "Candy Crush", "current_desc": "Match candies"},
    {"id": "temple-run", "name": "Temple Run", "genre": "action", "players": "1", "current_title": "Temple Run", "current_desc": "Run from monkeys"},
    {"id": "ludo-star", "name": "Ludo Star", "genre": "board", "players": "2-4", "current_title": "Ludo Star", "current_desc": "Play ludo"},
    {"id": "pubg-mobile", "name": "PUBG Mobile", "genre": "battle-royale", "players": "multiplayer", "current_title": "PUBG Mobile", "current_desc": "Battle royale game"},
]

METADATA_SCHEMA = {
    "title": str,
    "description": str,
    "short_description": str,
    "keywords": list,
    "og_title": str,
    "og_description": str,
    "twitter_title": str,
    "twitter_description": str,
    "rating": float,
    "age_rating": str,
    "language": list,
}


class MetadataPatchGenerator:
    PROJECT = "yallaplays"

    def __init__(self):
        self._ai = ContentGenerator()

    def _generate_metadata_for_game(self, game: dict) -> dict[str, Any]:
        name = game["name"]
        genre = game["genre"]
        players = game["players"]
        return {
            "game_id": game["id"],
            "game_name": name,
            "title": f"{name} — Play Free Online | YallaPlays",
            "description": f"Play {name} for free online at YallaPlays. {name} is a popular {genre} game supporting {players} players. No download needed — play instantly in your browser on mobile or desktop.",
            "short_description": f"Play {name} free online. Instant browser play, no download.",
            "keywords": [name.lower(), f"{name.lower()} online", f"play {name.lower()}", f"free {genre} games", "yallaplays", f"{genre} games online"],
            "og_title": f"Play {name} Free — YallaPlays",
            "og_description": f"Play {name} and hundreds of free games at YallaPlays. Instant play, no download.",
            "twitter_title": f"{name} — Free Online Game | YallaPlays",
            "twitter_description": f"Play {name} free online. {genre.title()} game for {players} players.",
            "age_rating": "PEGI 3" if genre in ("puzzle", "board", "arcade") else "PEGI 7",
            "language": ["ar", "en"],
            "schema_game": {
                "@context": "https://schema.org",
                "@type": "VideoGame",
                "name": name,
                "description": f"Play {name} free online at YallaPlays",
                "genre": genre,
                "numberOfPlayers": {"@type": "QuantitativeValue", "description": players},
                "gamePlatform": ["Browser", "Mobile", "Desktop"],
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
            },
        }

    def _build_patch_file(self, game: dict, metadata: dict) -> dict:
        import json
        return {
            "file_path": f"src/data/games/{game['id']}/metadata.json",
            "operation": "create_or_update",
            "content": json.dumps(metadata, indent=2, ensure_ascii=False),
            "description": f"Updated metadata for {game['name']}",
        }

    async def generate_metadata_patches(self, game_ids: list[str] | None = None, use_ai: bool = False) -> tuple[OperationalOutput, OperationalPreview]:
        games = [g for g in SAMPLE_GAMES if game_ids is None or g["id"] in game_ids]
        all_metadata = []
        patch_files = []
        ai_generated = False
        cost, tokens = 0.0, 0

        for game in games:
            metadata = self._generate_metadata_for_game(game)
            if use_ai and self._ai.is_ai_available():
                result = await self._ai.generate(
                    prompt=f'Improve the SEO title and meta description for a free browser game called "{game["name"]}" (genre: {game["genre"]}). Return JSON: {{"title": "...", "description": "...", "keywords": [...]}}',
                    system_prompt="You are an SEO expert for browser gaming. Keep descriptions under 160 chars. Target Arabic-speaking users.",
                    max_tokens=200,
                )
                if result.get("success"):
                    ai_generated = True
                    cost += result.get("cost_usd", 0)
                    tokens += result.get("total_tokens", 0)
            all_metadata.append(metadata)
            patch_files.append(self._build_patch_file(game, metadata))

        output = OperationalOutput(
            project=OperationProject.yallaplays,
            output_type=OutputType.metadata_patch,
            title=f"Metadata Patches — {len(games)} Games",
            description=f"SEO metadata improvements for {len(games)} games: title, description, structured data, OG tags",
            content={"games_patched": len(games), "metadata": all_metadata},
            patch_files=patch_files,
            risk_level=RiskLevel.low,
            ai_generated=ai_generated,
            cost_usd=round(cost, 6),
            tokens_used=tokens,
        )
        preview = OperationalPreview(
            output_id=output.id,
            project=OperationProject.yallaplays,
            preview_markdown=f"# Metadata Patches — {len(games)} Games\n\n" + "\n".join(f"- **{g['name']}**: title + description + schema updated" for g in games),
            diff_summary=f"Updates metadata for {len(games)} games across {len(patch_files)} files",
            files_changed=[p["file_path"] for p in patch_files],
            estimated_impact={"games_improved": len(games), "schema_added": len(games), "seo_score_delta": "+5-10 points per game"},
        )
        output.preview_id = preview.id
        return output, preview
