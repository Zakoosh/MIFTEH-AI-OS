from __future__ import annotations
from typing import Any
from ..content_generator import ContentGenerator
from ..models import OperationalOutput, OperationalPreview, OutputType, OperationProject, RiskLevel

CATEGORIES = {
    "popular": {"label": "Popular Games", "sort": "plays", "icon": "🔥", "description": "The most-played games on YallaPlays right now"},
    "new": {"label": "New Games", "sort": "created_at", "icon": "✨", "description": "Fresh games added to YallaPlays this week"},
    "trending": {"label": "Trending Games", "sort": "trend_score", "icon": "📈", "description": "Games everyone is talking about"},
    "multiplayer": {"label": "Multiplayer Games", "sort": "multiplayer_sessions", "icon": "👥", "description": "Play with friends online"},
    "arabic": {"label": "Arabic Games", "sort": "arabic_rating", "icon": "🌙", "description": "Games in Arabic — made for the Arab world"},
    "mobile": {"label": "Mobile Games", "sort": "mobile_plays", "icon": "📱", "description": "Best games optimised for mobile play"},
}


class CategoryPageGenerator:
    PROJECT = "yallaplays"

    def __init__(self):
        self._ai = ContentGenerator()

    def _build_category_config(self, category_key: str) -> dict[str, Any]:
        cat = CATEGORIES.get(category_key, {"label": category_key.title(), "sort": "plays", "icon": "🎮", "description": f"{category_key.title()} games on YallaPlays"})
        slug = category_key.lower()
        return {
            "category_key": category_key,
            "slug": slug,
            "label": cat["label"],
            "sort_field": cat["sort"],
            "icon": cat["icon"],
            "description": cat["description"],
            "url": f"https://yallaplays.com/games/{slug}/",
            "page_size": 24,
            "filters": ["genre", "rating", "players"],
            "sections": [
                {"id": "hero", "type": "hero_banner", "title": cat["label"], "subtitle": cat["description"]},
                {"id": "featured", "type": "featured_games", "count": 3, "label": f"Top {cat['label']}"},
                {"id": "grid", "type": "game_grid", "count": 24, "sort": cat["sort"], "label": "All Games"},
                {"id": "cta", "type": "newsletter_cta", "text": "Get weekly game picks in your inbox"},
            ],
            "seo": {
                "title": f"{cat['label']} — Free Online | YallaPlays",
                "description": f"{cat['description']}. Play free — no download, no registration.",
                "structured_type": "CollectionPage",
            },
            "filter_options": {
                "sort_by": [
                    {"value": cat["sort"], "label": "Most Relevant"},
                    {"value": "rating", "label": "Highest Rated"},
                    {"value": "new", "label": "Newest First"},
                ],
                "genre": ["Action", "Sports", "Puzzle", "Racing", "Strategy"],
                "players": ["Single Player", "Multiplayer", "Co-op"],
            },
        }

    def _render_page_patch(self, config: dict) -> str:
        return f"""import {{ CategoryLayout }} from '@/layouts/CategoryLayout';
import {{ GameGrid }} from '@/components/GameGrid';
import {{ HeroBanner }} from '@/components/HeroBanner';
import {{ FeaturedGames }} from '@/components/FeaturedGames';
import type {{ GetStaticProps }} from 'next';

interface Props {{ initialGames: Game[]; totalCount: number; }}

export default function {config['category_key'].title()}Category({{ initialGames, totalCount }}: Props) {{
  return (
    <CategoryLayout
      title="{config['seo']['title']}"
      description="{config['seo']['description']}"
      category="{config['category_key']}"
    >
      <HeroBanner
        title="{config['icon']} {config['label']}"
        subtitle="{config['description']}"
        totalCount={{totalCount}}
      />
      <FeaturedGames category="{config['category_key']}" limit={{3}} />
      <GameGrid
        category="{config['category_key']}"
        sortField="{config['sort_field']}"
        pageSize={{{config['page_size']}}}
        initialData={{initialGames}}
        filters={{{str(config['filter_options']['genre'])}}}
      />
    </CategoryLayout>
  );
}}

export const getStaticProps: GetStaticProps = async () => {{
  return {{ props: {{ initialGames: [], totalCount: 0 }}, revalidate: 300 }};
}};
"""

    async def generate_category_page(self, category_key: str, use_ai: bool = False) -> tuple[OperationalOutput, OperationalPreview]:
        config = self._build_category_config(category_key)
        ai_generated = False
        cost, tokens = 0.0, 0

        if use_ai and self._ai.is_ai_available():
            result = await self._ai.generate(
                prompt=f"Improve the hero section description and CTA copy for a YallaPlays '{config['label']}' category page. Return JSON with: hero_title, hero_subtitle, cta_text, filter_labels.",
                system_prompt="You are a UX copywriter for a gaming platform. Be engaging, brief, Arabic-culture-aware.",
                max_tokens=300,
            )
            if result.get("success"):
                ai_generated = True
                cost = result.get("cost_usd", 0)
                tokens = result.get("total_tokens", 0)

        patch_files = [
            {
                "file_path": f"src/pages/games/{config['slug']}/index.tsx",
                "operation": "create_or_update",
                "content": self._render_page_patch(config),
                "description": f"Category landing page for {config['label']}",
            },
            {
                "file_path": f"src/config/categories/{config['slug']}.json",
                "operation": "create_or_update",
                "content": str(config),
                "description": f"Category configuration for {config['category_key']}",
            },
        ]

        output = OperationalOutput(
            project=OperationProject.yallaplays,
            output_type=OutputType.category_page,
            title=f"Category Page — {config['label']}",
            description=f"Landing page for {config['label']} with filters, hero, and game grid",
            content=config,
            patch_files=patch_files,
            risk_level=RiskLevel.low,
            ai_generated=ai_generated,
            cost_usd=cost,
            tokens_used=tokens,
        )
        preview = OperationalPreview(
            output_id=output.id,
            project=OperationProject.yallaplays,
            preview_markdown=f"# Category Page — {config['label']}\n\n**URL**: {config['url']}\n\n**Sections**: {', '.join(s['type'] for s in config['sections'])}\n\n**Files**: {len(patch_files)} files updated",
            diff_summary=f"Creates {config['label']} category landing page with {len(config['sections'])} sections",
            files_changed=[p["file_path"] for p in patch_files],
            estimated_impact={"new_indexable_page": True, "filter_ux": "improved", "bounce_rate_impact": "-5% estimated"},
        )
        output.preview_id = preview.id
        return output, preview

    async def generate_all_categories(self, use_ai: bool = False) -> list[tuple[OperationalOutput, OperationalPreview]]:
        results = []
        for key in CATEGORIES:
            output, preview = await self.generate_category_page(key, use_ai=use_ai)
            results.append((output, preview))
        return results
