"""
seo_apply.py — SEO improvement applier for YallaPlays.

Handles:
  • SEO metadata (title, description, keywords, OG tags)
  • Landing page copy updates
  • Category label / ordering optimizations
  • Web app manifest improvements
"""

from __future__ import annotations

from typing import Any

from .models import Proposal


# ---------------------------------------------------------------------------
# Built-in proposal templates (seeded if no custom proposals exist)
# ---------------------------------------------------------------------------

YALLAPLAYS_SEO_PROPOSALS: list[dict] = [
    {
        "id": "seo_lp_001",
        "project_id": "yallaplays",
        "proposal_type": "seo",
        "title": "Improve YallaPlays homepage SEO metadata",
        "description": "Update title, meta description, and OG tags for better search visibility.",
        "target_file": "public/index.html",
        "changes": {
            "title": "YallaPlays — Play Free Online Games in Arabic & English",
            "description": "Discover hundreds of free online games on YallaPlays. Play instantly, no download needed.",
            "keywords": "free online games, Arabic games, play games online, YallaPlays",
            "og_title": "YallaPlays — Free Online Games",
            "og_description": "Play the best free online games. New games added weekly.",
            "og_image": "/assets/og-home.jpg",
            "twitter_card": "summary_large_image",
            "canonical_url": "https://yallaplays.com/",
        },
        "risk_level": "low",
        "tags": ["seo", "homepage", "metadata"],
    },
    {
        "id": "seo_cat_001",
        "project_id": "yallaplays",
        "proposal_type": "category",
        "title": "Optimize game category display order",
        "description": "Move Action and Sports categories to top positions for higher engagement.",
        "target_file": "src/data/categories.json",
        "changes": {
            "category_name": "Action Games",
            "display_order": 1,
            "is_featured": True,
            "category_description": "Fast-paced action games for all ages",
        },
        "risk_level": "low",
        "tags": ["category", "ux", "engagement"],
    },
    {
        "id": "seo_manifest_001",
        "project_id": "yallaplays",
        "proposal_type": "manifest",
        "title": "Improve PWA manifest for YallaPlays",
        "description": "Enhance web app manifest for better installability and branding.",
        "target_file": "public/manifest.json",
        "changes": {
            "name": "YallaPlays — Online Games",
            "short_name": "YallaPlays",
            "description": "Play free online games — no download required",
            "theme_color": "#1a1a2e",
            "background_color": "#0f3460",
            "display": "standalone",
        },
        "risk_level": "low",
        "tags": ["manifest", "pwa", "branding"],
    },
    {
        "id": "seo_lp_002",
        "project_id": "yallaplays",
        "proposal_type": "landing_page",
        "title": "Update YallaPlays hero section copy",
        "description": "Improve hero headline and CTA for better conversion.",
        "target_file": "src/config/landing.json",
        "changes": {
            "hero_title": "Play Free Games — Anytime, Anywhere",
            "hero_subtitle": "500+ games available instantly. No signup needed.",
            "cta_text": "Start Playing Now",
            "cta_url": "/games",
            "testimonials_enabled": True,
        },
        "risk_level": "low",
        "tags": ["landing_page", "conversion", "copy"],
    },
]


# ---------------------------------------------------------------------------
# SEOApplier
# ---------------------------------------------------------------------------

class SEOApplier:
    """Generates structured change sets for SEO-related proposals."""

    def prepare_changes(self, proposal: Proposal) -> dict[str, Any]:
        """Dispatch to the appropriate handler based on proposal_type."""
        handler_map = {
            "seo": self._prepare_seo_metadata,
            "landing_page": self._prepare_landing_page,
            "category": self._prepare_category,
            "manifest": self._prepare_manifest,
        }
        handler = handler_map.get(proposal.proposal_type, self._prepare_generic)
        return handler(proposal)

    def generate_preview_summary(self, proposal: Proposal) -> tuple[str, str]:
        """Return (before_summary, after_summary) strings for the preview."""
        before = f"[{proposal.proposal_type.upper()}] Current state of {proposal.target_file}"
        after_lines = [f"  • {k}: {v}" for k, v in proposal.changes.items()]
        after = f"Proposed changes:\n" + "\n".join(after_lines)
        return before, after

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _prepare_seo_metadata(self, proposal: Proposal) -> dict[str, Any]:
        return {
            "seo_update": True,
            **proposal.changes,
        }

    def _prepare_landing_page(self, proposal: Proposal) -> dict[str, Any]:
        return {
            "landing_page_update": True,
            **proposal.changes,
        }

    def _prepare_category(self, proposal: Proposal) -> dict[str, Any]:
        return {
            "category_update": True,
            **proposal.changes,
        }

    def _prepare_manifest(self, proposal: Proposal) -> dict[str, Any]:
        return {
            "manifest_update": True,
            **proposal.changes,
        }

    def _prepare_generic(self, proposal: Proposal) -> dict[str, Any]:
        return dict(proposal.changes)


# Module-level singleton
seo_applier = SEOApplier()


def get_builtin_proposals() -> list[dict]:
    """Return the list of built-in YallaPlays SEO proposals."""
    return YALLAPLAYS_SEO_PROPOSALS
