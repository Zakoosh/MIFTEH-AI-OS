"""
metadata_apply.py — Metadata improvement applier for both projects.

Handles structured data (JSON-LD), OG tags, page titles, and
language/viewport metadata across YallaPlays and Fionera.
"""

from __future__ import annotations

from typing import Any

from .models import Proposal


# ---------------------------------------------------------------------------
# Built-in metadata proposals
# ---------------------------------------------------------------------------

METADATA_PROPOSALS: list[dict] = [
    {
        "id": "meta_yp_001",
        "project_id": "yallaplays",
        "proposal_type": "metadata",
        "title": "Add structured data to YallaPlays game pages",
        "description": "Inject JSON-LD schema for GameApplication type to improve rich results.",
        "target_file": "src/config/metadata.json",
        "changes": {
            "schema_type": "GameApplication",
            "author": "YallaPlays",
            "language": "ar,en",
            "viewport": "width=device-width, initial-scale=1",
            "page_title": "YallaPlays — Free Online Games",
            "meta_description": "Play 500+ free online games on YallaPlays. No download needed.",
        },
        "risk_level": "low",
        "tags": ["metadata", "schema", "seo"],
    },
    {
        "id": "meta_fi_001",
        "project_id": "fionera",
        "proposal_type": "metadata",
        "title": "Improve Fionera page metadata",
        "description": "Update meta tags for Fionera investment dashboard pages.",
        "target_file": "src/config/metadata.json",
        "changes": {
            "page_title": "Fionera — Smart Investment Dashboard",
            "meta_description": "Track your portfolio, analyze markets, and grow your investments with Fionera.",
            "schema_type": "WebApplication",
            "author": "Fionera",
            "language": "en",
        },
        "risk_level": "low",
        "tags": ["metadata", "dashboard", "seo"],
    },
]


# ---------------------------------------------------------------------------
# MetadataApplier
# ---------------------------------------------------------------------------

class MetadataApplier:
    """Prepares and previews metadata change sets."""

    def prepare_changes(self, proposal: Proposal) -> dict[str, Any]:
        """Return structured changes ready for patch generation."""
        return {
            "metadata_update": True,
            "project": proposal.project_id,
            **proposal.changes,
        }

    def generate_preview_summary(self, proposal: Proposal) -> tuple[str, str]:
        before = f"[METADATA] Current metadata for {proposal.project_id} — {proposal.target_file}"
        after_lines = [f"  • {k}: {v}" for k, v in proposal.changes.items()]
        after = "Proposed metadata changes:\n" + "\n".join(after_lines)
        return before, after

    def build_json_ld(self, schema_type: str, data: dict[str, Any]) -> dict:
        """Build a JSON-LD structured data block."""
        return {
            "@context": "https://schema.org",
            "@type": schema_type,
            **{k: v for k, v in data.items() if not k.startswith("_")},
        }


# Module-level singleton
metadata_applier = MetadataApplier()


def get_builtin_proposals() -> list[dict]:
    return METADATA_PROPOSALS
