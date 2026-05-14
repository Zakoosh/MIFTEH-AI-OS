from __future__ import annotations
from datetime import datetime
from typing import Any
from ..content_generator import ContentGenerator
from ..models import OperationalOutput, OperationalPreview, OutputType, OperationProject, RiskLevel

GAME_CATEGORIES = [
    "Action Games", "Sports Games", "Racing Games", "Puzzle Games",
    "Strategy Games", "RPG Games", "Arcade Games", "Multiplayer Games",
    "Card Games", "Casino Games", "Adventure Games", "Shooting Games",
]

SEO_TEMPLATES = {
    "action": {
        "title": "Best {category} Online — Play Free on YallaPlays",
        "meta_description": "Play the best {category} online for free on YallaPlays. No download needed — instant play on mobile and desktop. Discover new {category} daily.",
        "h1": "Free {category} — Play Instantly Online",
        "intro": "YallaPlays offers the largest collection of free {category} in the Arab world. Whether you prefer fast-paced shooters, fighting games, or platformers, find your next favourite game here. All games are playable directly in your browser — no download, no registration required.",
        "keywords": ["{category_slug}", "free {category_slug}", "{category_slug} online", "play {category_slug}", "best {category_slug} 2025"],
    },
    "sports": {
        "title": "Free Sports Games Online — Football, Basketball & More | YallaPlays",
        "meta_description": "Play free sports games online at YallaPlays. Football, basketball, cricket, and more — all playable in your browser, no download needed.",
        "h1": "Sports Games — Play Free Online",
        "intro": "Experience the thrill of your favourite sports from your browser. YallaPlays brings you a massive library of free sports games including football, basketball, cricket, and tennis. Compete against friends or challenge the AI — the stadium is always open.",
        "keywords": ["sports games online", "free football games", "basketball games online", "cricket games browser"],
    },
}

STRUCTURED_DATA_TEMPLATE = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    "name": "{title}",
    "description": "{meta_description}",
    "url": "https://yallaplays.com/games/{category_slug}/",
    "publisher": {"@type": "Organization", "name": "YallaPlays", "url": "https://yallaplays.com"},
}


class YallaPlaysSEOGenerator:
    PROJECT = "yallaplays"
    SITE_URL = "https://yallaplays.com"

    def __init__(self):
        self._ai = ContentGenerator()

    def _slug(self, text: str) -> str:
        return text.lower().replace(" ", "-").replace("&", "and")

    def _build_template_output(self, category: str) -> dict[str, Any]:
        slug = self._slug(category)
        tmpl = SEO_TEMPLATES.get("action")
        title = tmpl["title"].replace("{category}", category)
        meta_desc = tmpl["meta_description"].replace("{category}", category)
        h1 = tmpl["h1"].replace("{category}", category)
        intro = tmpl["intro"].replace("{category}", category).replace("{category_slug}", slug)
        keywords = [k.replace("{category_slug}", slug).replace("{category}", category) for k in tmpl["keywords"]]
        structured = {k: v.replace("{title}", title).replace("{meta_description}", meta_desc).replace("{category_slug}", slug) if isinstance(v, str) else v for k, v in STRUCTURED_DATA_TEMPLATE.items()}

        page_path = f"games/{slug}/"
        return {
            "page_path": page_path,
            "full_url": f"{self.SITE_URL}/{page_path}",
            "title_tag": title,
            "meta_description": meta_desc,
            "h1": h1,
            "intro_paragraph": intro,
            "keywords": keywords,
            "structured_data": structured,
            "canonical": f"{self.SITE_URL}/{page_path}",
            "og_title": title,
            "og_description": meta_desc,
            "og_type": "website",
            "breadcrumb": [
                {"name": "Home", "url": self.SITE_URL},
                {"name": "Games", "url": f"{self.SITE_URL}/games/"},
                {"name": category, "url": f"{self.SITE_URL}/{page_path}"},
            ],
            "internal_links": [
                {"text": "All Games", "url": f"{self.SITE_URL}/games/"},
                {"text": "Popular Games", "url": f"{self.SITE_URL}/games/popular/"},
                {"text": "New Games", "url": f"{self.SITE_URL}/games/new/"},
            ],
        }

    def _build_patch_files(self, category: str, content: dict) -> list[dict]:
        slug = self._slug(category)
        return [
            {
                "file_path": f"src/pages/games/{slug}/index.tsx",
                "operation": "create_or_update",
                "content_type": "react_page",
                "description": f"SEO-optimised category page for {category}",
                "content": self._render_page_component(category, content),
            },
            {
                "file_path": f"src/pages/games/{slug}/seo.ts",
                "operation": "create_or_update",
                "content_type": "seo_metadata",
                "description": f"SEO metadata exports for {category} page",
                "content": self._render_seo_metadata(content),
            },
        ]

    def _render_page_component(self, category: str, content: dict) -> str:
        return f"""import {{ SEOHead }} from '@/components/SEOHead';
import {{ GameGrid }} from '@/components/GameGrid';
import {{ Breadcrumb }} from '@/components/Breadcrumb';

export default function {category.replace(' ', '')}Page() {{
  return (
    <>
      <SEOHead
        title="{content['title_tag']}"
        description="{content['meta_description']}"
        canonical="{content['canonical']}"
      />
      <main className="container mx-auto px-4 py-8">
        <Breadcrumb items={{{str(content['breadcrumb'])}}} />
        <h1 className="text-3xl font-bold mb-4">{content['h1']}</h1>
        <p className="text-gray-600 mb-8">{content['intro_paragraph']}</p>
        <GameGrid category="{self._slug(category)}" limit={{24}} />
      </main>
    </>
  );
}}
"""

    def _render_seo_metadata(self, content: dict) -> str:
        import json
        return f"""export const seoMeta = {{
  title: "{content['title_tag']}",
  description: "{content['meta_description']}",
  keywords: {json.dumps(content['keywords'])},
  canonical: "{content['canonical']}",
  og: {{
    title: "{content['og_title']}",
    description: "{content['og_description']}",
    type: "{content['og_type']}",
  }},
  structuredData: {json.dumps(content['structured_data'], indent=2)},
}};
"""

    async def generate_seo_page(self, category: str, use_ai: bool = False) -> tuple[OperationalOutput, OperationalPreview]:
        if use_ai and self._ai.is_ai_available():
            ai_result = await self._ai.generate(
                prompt=f"""Generate SEO content for a YallaPlays category page for "{category}" games.
Return JSON with: title_tag, meta_description, h1, intro_paragraph (2-3 sentences), keywords (list of 8).
The site is YallaPlays - a free online gaming platform popular in the Arab world.""",
                system_prompt="You are an SEO expert specialising in gaming websites. Return valid JSON only.",
                max_tokens=600,
            )
            if ai_result.get("success"):
                content = self._build_template_output(category)
                content.update(ai_result.get("structured", {}).get("raw", content))
                ai_generated = True
                cost = ai_result.get("cost_usd", 0)
                tokens = ai_result.get("total_tokens", 0)
                provider = "openai"
            else:
                content = self._build_template_output(category)
                ai_generated = False
                cost, tokens, provider = 0.0, 0, "template"
        else:
            content = self._build_template_output(category)
            ai_generated = False
            cost, tokens, provider = 0.0, 0, "template"

        patch_files = self._build_patch_files(category, content)
        output = OperationalOutput(
            project=OperationProject.yallaplays,
            output_type=OutputType.seo_page,
            title=f"SEO Page — {category}",
            description=f"SEO-optimised category landing page for {category} on YallaPlays",
            content=content,
            patch_files=patch_files,
            risk_level=RiskLevel.low,
            ai_generated=ai_generated,
            provider_used=provider,
            tokens_used=tokens,
            cost_usd=cost,
        )

        preview = OperationalPreview(
            output_id=output.id,
            project=OperationProject.yallaplays,
            preview_markdown=self._build_preview_markdown(category, content),
            diff_summary=f"Creates/updates {len(patch_files)} files for {category} SEO page",
            files_changed=[p["file_path"] for p in patch_files],
            estimated_impact={
                "seo_score_improvement": "+15-25 points",
                "pages_indexed": 1,
                "target_keywords": len(content.get("keywords", [])),
                "estimated_organic_traffic_gain": "200-500 visits/month",
            },
        )
        output.preview_id = preview.id

        return output, preview

    def _build_preview_markdown(self, category: str, content: dict) -> str:
        return f"""# SEO Page Preview — {category}

## Meta Tags
- **Title**: {content['title_tag']}
- **Description**: {content['meta_description']}
- **Canonical**: {content['canonical']}

## Page Content
### {content['h1']}
{content['intro_paragraph']}

## Target Keywords
{chr(10).join(f"- {k}" for k in content.get('keywords', []))}

## Structured Data
- Type: CollectionPage
- Publisher: YallaPlays

## Files Changed
{chr(10).join(f"- `{p['file_path']}`" for p in self._build_patch_files(category, content))}

---
*Preview-only — requires approval before apply*
"""

    async def generate_batch(self, categories: list[str] | None = None, use_ai: bool = False) -> list[tuple[OperationalOutput, OperationalPreview]]:
        targets = categories or GAME_CATEGORIES
        results = []
        for cat in targets:
            output, preview = await self.generate_seo_page(cat, use_ai=use_ai)
            results.append((output, preview))
        return results
