from __future__ import annotations
from typing import Any
from ..models import OperationalOutput, OperationalPreview, OutputType, OperationProject, RiskLevel
from ..content_generator import ContentGenerator

LINK_OPPORTUNITIES = [
    {"source": "/games/action/", "target": "/games/shooting/", "anchor": "Shooting Games", "relevance": "high"},
    {"source": "/games/sports/", "target": "/games/football/", "anchor": "Football Games", "relevance": "high"},
    {"source": "/games/puzzle/", "target": "/games/card/", "anchor": "Card & Board Games", "relevance": "medium"},
    {"source": "/games/racing/", "target": "/games/mobile/", "anchor": "Best Mobile Games", "relevance": "high"},
    {"source": "/", "target": "/games/trending/", "anchor": "Trending Games", "relevance": "high"},
    {"source": "/", "target": "/games/new/", "anchor": "New Games", "relevance": "high"},
    {"source": "/games/multiplayer/", "target": "/games/arabic/", "anchor": "Arabic Games", "relevance": "medium"},
    {"source": "/games/popular/", "target": "/games/multiplayer/", "anchor": "Play With Friends", "relevance": "high"},
]

NAVIGATION_IMPROVEMENTS = {
    "breadcrumb_schema": True,
    "related_games_widget": True,
    "category_crosslinks": True,
    "footer_sitemap": True,
    "game_tags": True,
}


class InternalLinkingGenerator:
    PROJECT = "yallaplays"

    def __init__(self):
        self._ai = ContentGenerator()

    def _build_link_graph(self) -> dict[str, Any]:
        from collections import defaultdict
        graph: dict[str, list] = defaultdict(list)
        for link in LINK_OPPORTUNITIES:
            graph[link["source"]].append({
                "target": link["target"],
                "anchor_text": link["anchor"],
                "relevance": link["relevance"],
            })
        return dict(graph)

    def _build_related_games_component(self) -> str:
        return """import Link from 'next/link';

interface RelatedCategory { slug: string; label: string; count: number; }

export function RelatedCategories({ categories }: { categories: RelatedCategory[] }) {
  return (
    <section className="related-categories mt-8">
      <h2 className="text-xl font-bold mb-4">You Might Also Like</h2>
      <div className="flex flex-wrap gap-2">
        {categories.map(cat => (
          <Link
            key={cat.slug}
            href={`/games/${cat.slug}/`}
            className="px-4 py-2 bg-blue-50 hover:bg-blue-100 rounded-full text-sm font-medium"
          >
            {cat.label} ({cat.count})
          </Link>
        ))}
      </div>
    </section>
  );
}
"""

    def _build_breadcrumb_component(self) -> str:
        return """import Link from 'next/link';

interface Crumb { name: string; url: string; }

export function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="mb-4">
      <ol className="flex flex-wrap gap-1 text-sm text-gray-500" itemScope itemType="https://schema.org/BreadcrumbList">
        {items.map((item, i) => (
          <li key={item.url} itemProp="itemListElement" itemScope itemType="https://schema.org/ListItem">
            {i < items.length - 1 ? (
              <><Link href={item.url} itemProp="item" className="hover:text-blue-600"><span itemProp="name">{item.name}</span></Link><span className="mx-1">/</span></>
            ) : (
              <span itemProp="name" className="text-gray-900 font-medium">{item.name}</span>
            )}
            <meta itemProp="position" content={String(i + 1)} />
          </li>
        ))}
      </ol>
    </nav>
  );
}
"""

    async def generate_internal_linking(self, use_ai: bool = False) -> tuple[OperationalOutput, OperationalPreview]:
        link_graph = self._build_link_graph()
        high_priority = [l for l in LINK_OPPORTUNITIES if l["relevance"] == "high"]
        ai_generated = False
        cost, tokens = 0.0, 0

        if use_ai and self._ai.is_ai_available():
            result = await self._ai.generate(
                prompt="Suggest 5 additional internal linking opportunities for a gaming website with categories: Action, Sports, Racing, Puzzle, Multiplayer, Arabic Games, New, Popular, Trending. Return JSON: [{source, target, anchor_text, reason}]",
                system_prompt="You are an SEO specialist. Focus on topical relevance and user journey flow.",
                max_tokens=400,
            )
            if result.get("success"):
                ai_generated = True
                cost = result.get("cost_usd", 0)
                tokens = result.get("total_tokens", 0)

        patch_files = [
            {
                "file_path": "src/components/RelatedCategories.tsx",
                "operation": "create",
                "content": self._build_related_games_component(),
                "description": "Related categories widget for internal linking",
            },
            {
                "file_path": "src/components/Breadcrumb.tsx",
                "operation": "create_or_update",
                "content": self._build_breadcrumb_component(),
                "description": "Schema.org breadcrumb component",
            },
            {
                "file_path": "src/data/internal-links.json",
                "operation": "create_or_update",
                "content": str(link_graph),
                "description": "Internal linking graph configuration",
            },
        ]

        output = OperationalOutput(
            project=OperationProject.yallaplays,
            output_type=OutputType.internal_linking,
            title=f"Internal Linking — {len(LINK_OPPORTUNITIES)} Opportunities",
            description=f"Internal linking improvements: {len(high_priority)} high-priority links, breadcrumb schema, related categories widget",
            content={"link_graph": link_graph, "total_links": len(LINK_OPPORTUNITIES), "high_priority": len(high_priority)},
            patch_files=patch_files,
            risk_level=RiskLevel.low,
            ai_generated=ai_generated,
            cost_usd=cost,
            tokens_used=tokens,
        )
        preview = OperationalPreview(
            output_id=output.id,
            project=OperationProject.yallaplays,
            preview_markdown=f"# Internal Linking Plan\n\n## {len(LINK_OPPORTUNITIES)} Link Opportunities\n\n" + "\n".join(f"- `{l['source']}` → `{l['target']}` ({l['anchor']}) [{l['relevance']}]" for l in LINK_OPPORTUNITIES),
            diff_summary=f"Adds {len(patch_files)} files for internal linking infrastructure",
            files_changed=[p["file_path"] for p in patch_files],
            estimated_impact={"page_authority_flow": "improved", "crawl_depth": "reduced", "seo_score_delta": "+8-12 points", "user_engagement": "+5% pages/session"},
        )
        output.preview_id = preview.id
        return output, preview
