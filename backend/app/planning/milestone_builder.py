"""
milestone_builder.py — Generates business milestones from work item sets.

Milestones are grouped by (project, quarter, theme).  Each milestone maps
to a set of work items and carries success criteria and deliverables.
"""

from __future__ import annotations

from typing import Any

from .models import Milestone, STATUS_PENDING


# ---------------------------------------------------------------------------
# Milestone templates keyed by (project, theme_key)
# ---------------------------------------------------------------------------

_MILESTONE_DEFS: dict[str, dict] = {

    # ── YallaPlays ──────────────────────────────────────────────────────────

    "yallaplays_technical_foundation": {
        "project": "yallaplays",
        "quarter": "Q3-2026",
        "title": "Technical Foundation Complete",
        "description": "Core Web Vitals are all-green; CDN migration live; fast, crawlable pages.",
        "phase": "preparation",
        "success_criteria": [
            "LCP < 2.5 s on all category pages (Lighthouse CI)",
            "CLS < 0.1 on homepage and top 20 pages",
            "CDN serving ≥ 95% of static assets",
            "XML sitemap refreshed and submitted to Search Console",
        ],
        "deliverables": [
            "Lighthouse performance report",
            "CDN migration runbook",
            "Core Web Vitals monitoring dashboard",
        ],
        "work_item_ids": ["wi_yp_003", "wi_yp_012"],
        "estimated_completion_days": 14,
        "estimated_effort_days": 14,
        "priority": "critical",
    },

    "yallaplays_seo_discovery": {
        "project": "yallaplays",
        "quarter": "Q3-2026",
        "title": "SEO & Discovery Launch",
        "description": "Topical SEO clusters live; game search operational; ASO updated.",
        "phase": "implementation",
        "success_criteria": [
            "3 genre cluster hub pages indexed (survival, multiplayer, puzzle)",
            "Game search returning results in < 200 ms",
            "App Store listing updated with new screenshots",
            "All new pages have valid JSON-LD structured data",
        ],
        "deliverables": [
            "3 SEO cluster landing pages",
            "Game search with fuzzy matching",
            "Updated App Store listing",
            "Schema validation report",
        ],
        "work_item_ids": ["wi_yp_001", "wi_yp_002", "wi_yp_004", "wi_yp_009", "wi_yp_013"],
        "estimated_completion_days": 35,
        "estimated_effort_days": 45,
        "priority": "high",
    },

    "yallaplays_retention_engine": {
        "project": "yallaplays",
        "quarter": "Q3-2026",
        "title": "Retention Engine Live",
        "description": "Personalised recommendations, daily challenges, and mobile redesign shipped.",
        "phase": "implementation",
        "success_criteria": [
            "Recommendation engine serving suggestions on homepage for ≥ 80% sessions",
            "Daily challenge feature live with streak counter",
            "Mobile game card redesign rolled out to 100%",
            "D7 retention ≥ 25%",
        ],
        "deliverables": [
            "Recommendation API (collaborative filtering model)",
            "Daily challenge mechanic + streak reward system",
            "Redesigned mobile game cards",
            "Retention analytics dashboard",
        ],
        "work_item_ids": ["wi_yp_005", "wi_yp_007", "wi_yp_010", "wi_yp_015"],
        "estimated_completion_days": 56,
        "estimated_effort_days": 46,
        "priority": "high",
    },

    "yallaplays_social_monetisation": {
        "project": "yallaplays",
        "quarter": "Q4-2026",
        "title": "Social & Monetisation Layer",
        "description": "Leaderboards, achievements, onboarding, and rewarded ads shipped.",
        "phase": "deployment",
        "success_criteria": [
            "Global + friend leaderboards live for top 50 games",
            "Achievement system with ≥ 20 badges unlockable",
            "Rewarded video ad revenue ≥ $2k/month",
            "D1 retention for new users ≥ 50%",
        ],
        "deliverables": [
            "Leaderboard service and social challenge mechanic",
            "Achievement badge system + trophy room",
            "Onboarding flow (3-step genre selection)",
            "Rewarded ad integration + revenue dashboard",
        ],
        "work_item_ids": ["wi_yp_006", "wi_yp_008", "wi_yp_011", "wi_yp_014"],
        "estimated_completion_days": 84,
        "estimated_effort_days": 57,
        "priority": "medium",
    },

    # ── Fionera ─────────────────────────────────────────────────────────────

    "fionera_ux_foundation": {
        "project": "fionera",
        "quarter": "Q3-2026",
        "title": "UX Foundation Ready",
        "description": "Dark mode, redesigned mobile navigation, and Market Overview widget live.",
        "phase": "preparation",
        "success_criteria": [
            "Dark mode available on all screens with system-preference detection",
            "Bottom tab navigation shipped in iOS + Android builds",
            "Market Overview widget displaying 8+ major indices",
            "Design token system documented",
        ],
        "deliverables": [
            "Dark mode implementation + design token system",
            "Redesigned mobile bottom navigation",
            "Market Overview widget",
            "Mobile app update (iOS + Android)",
        ],
        "work_item_ids": ["wi_fi_011", "wi_fi_016", "wi_fi_017"],
        "estimated_completion_days": 14,
        "estimated_effort_days": 22,
        "priority": "high",
    },

    "fionera_ai_intelligence": {
        "project": "fionera",
        "quarter": "Q3-2026",
        "title": "AI Intelligence Core Live",
        "description": "AI Risk Score, dividend tracker, multi-currency, and smart alerts shipped.",
        "phase": "implementation",
        "success_criteria": [
            "AI Risk Score widget adopted by ≥ 60% of active users",
            "Dividend tracker showing forward yield and ex-div dates",
            "Multi-currency support for ≥ 10 currencies with live FX",
            "Smart price alerts delivering push + email within 30 s of trigger",
        ],
        "deliverables": [
            "AI Risk Scoring API + widget",
            "Dividend income tracker + DRIP simulator",
            "Multi-currency P&L engine",
            "Smart alert rule engine + notification service",
        ],
        "work_item_ids": ["wi_fi_001", "wi_fi_003", "wi_fi_004", "wi_fi_005", "wi_fi_010"],
        "estimated_completion_days": 35,
        "estimated_effort_days": 62,
        "priority": "critical",
    },

    "fionera_revenue_launch": {
        "project": "fionera",
        "quarter": "Q3-2026",
        "title": "Revenue Launch",
        "description": "Premium tier, redesigned dashboard, and SEO hub live.",
        "phase": "deployment",
        "success_criteria": [
            "Premium tier (Pro + Institutional) accepting payments via Stripe",
            "Dashboard redesign rolled out to 100% of users",
            "SEO hub indexed with portfolio-tracker cluster",
            "MRR ≥ $20k within 30 days of launch",
        ],
        "deliverables": [
            "Stripe billing integration (Pro + Institutional tiers)",
            "Redesigned portfolio dashboard",
            "SEO portfolio-tracker landing page cluster",
            "Revenue analytics dashboard",
        ],
        "work_item_ids": ["wi_fi_008", "wi_fi_009", "wi_fi_018"],
        "estimated_completion_days": 56,
        "estimated_effort_days": 50,
        "priority": "critical",
    },

    "fionera_advanced_analytics": {
        "project": "fionera",
        "quarter": "Q4-2026",
        "title": "Advanced Analytics & Social Growth",
        "description": "Tax reporting, benchmarking, rebalancing, watchlist sharing, and attribution.",
        "phase": "implementation",
        "success_criteria": [
            "Tax report generation available for premium users in ≥ 5 countries",
            "Benchmark comparison vs S&P 500 + NASDAQ for all users",
            "Watchlist sharing with public URLs and clone action",
            "Performance attribution waterfall chart available",
        ],
        "deliverables": [
            "Capital gains tax report (PDF export)",
            "Portfolio benchmark comparison engine",
            "Automated rebalancing recommendation alert",
            "Watchlist sharing + social discovery feed",
            "Performance attribution analytics",
        ],
        "work_item_ids": ["wi_fi_002", "wi_fi_006", "wi_fi_007",
                          "wi_fi_012", "wi_fi_013", "wi_fi_014", "wi_fi_015"],
        "estimated_completion_days": 84,
        "estimated_effort_days": 79,
        "priority": "medium",
    },
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_milestones(
    items: list[Any],
    project: str = "all",
) -> list[Milestone]:
    """Return milestones relevant to the given project and work items."""
    item_ids = {i.item_id for i in items}

    milestones: list[Milestone] = []
    for key, defn in _MILESTONE_DEFS.items():
        ms_project = defn["project"]
        if project not in ("all", ms_project):
            continue

        # Only include milestones whose work items overlap with the provided set
        overlap = [wid for wid in defn["work_item_ids"] if wid in item_ids]
        if not overlap:
            continue

        ms = Milestone(
            milestone_id               = f"ms_{key}",
            project                    = ms_project,
            quarter                    = defn["quarter"],
            title                      = defn["title"],
            description                = defn["description"],
            phase                      = defn["phase"],
            success_criteria           = defn["success_criteria"],
            work_item_ids              = defn["work_item_ids"],
            plan_ids                   = [f"plan_{wid}" for wid in defn["work_item_ids"]],
            deliverables               = defn["deliverables"],
            estimated_completion_days  = defn["estimated_completion_days"],
            estimated_effort_days      = defn["estimated_effort_days"],
            priority                   = defn["priority"],
            status                     = STATUS_PENDING,
        )
        milestones.append(ms)

    return milestones


def get_milestone_for_item(item_id: str) -> list[str]:
    """Return milestone IDs that contain the given work_item_id."""
    return [
        f"ms_{key}"
        for key, defn in _MILESTONE_DEFS.items()
        if item_id in defn["work_item_ids"]
    ]
