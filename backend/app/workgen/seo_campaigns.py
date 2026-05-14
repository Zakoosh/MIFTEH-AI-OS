"""
seo_campaigns.py — SEO campaign catalog for YallaPlays and Fionera.
"""

from __future__ import annotations

from .models import Campaign, PRIORITY_HIGH, PRIORITY_MEDIUM, EFFORT_MEDIUM, EFFORT_HIGH


def get_yallaplays_campaigns() -> list[Campaign]:
    return [
        Campaign(
            campaign_id="cam_yp_seo_001",
            project="yallaplays",
            campaign_type="seo",
            title="Build Survival Games SEO Cluster",
            description=(
                "Create a topical authority cluster around survival games: hub page, "
                "sub-pages per sub-genre (battle royale, crafting, zombie), internal linking, "
                "and schema markup."
            ),
            target_keywords=["survival games", "best survival games", "survival games online",
                             "battle royale games", "zombie survival games"],
            target_pages=["/games/survival", "/games/battle-royale", "/games/zombie-survival"],
            estimated_impact=88.0,
            estimated_effort=EFFORT_MEDIUM,
            timeline_weeks=6,
            recommended_agents=["marketing-seo-specialist", "engineering-frontend-developer"],
            monthly_search_volume=320000,
            difficulty_score=58.0,
            priority=PRIORITY_HIGH,
        ),
        Campaign(
            campaign_id="cam_yp_seo_002",
            project="yallaplays",
            campaign_type="seo",
            title="Multiplayer Games Discovery Hub",
            description=(
                "Build a discovery hub for multiplayer games with category pages, "
                "player-count filters, and rich snippets optimized for 'play multiplayer games' queries."
            ),
            target_keywords=["multiplayer games", "online multiplayer games", "free multiplayer games",
                             "browser multiplayer", "2 player games"],
            target_pages=["/games/multiplayer", "/games/2-player", "/games/co-op"],
            estimated_impact=85.0,
            estimated_effort=EFFORT_MEDIUM,
            timeline_weeks=5,
            recommended_agents=["marketing-seo-specialist", "engineering-frontend-developer",
                                 "product-manager"],
            monthly_search_volume=450000,
            difficulty_score=62.0,
            priority=PRIORITY_HIGH,
        ),
        Campaign(
            campaign_id="cam_yp_seo_003",
            project="yallaplays",
            campaign_type="seo",
            title="Puzzle Games Long-Tail Content Expansion",
            description=(
                "Target long-tail puzzle game queries with category pages, difficulty filters, "
                "and FAQ schema to capture 'easy puzzle games for kids' and related terms."
            ),
            target_keywords=["puzzle games", "easy puzzle games", "puzzle games for kids",
                             "brain teaser games", "logic games online"],
            target_pages=["/games/puzzle", "/games/puzzle/easy", "/games/puzzle/kids"],
            estimated_impact=78.0,
            estimated_effort=EFFORT_MEDIUM,
            timeline_weeks=4,
            recommended_agents=["marketing-seo-specialist", "content-writer"],
            monthly_search_volume=280000,
            difficulty_score=45.0,
            priority=PRIORITY_HIGH,
        ),
        Campaign(
            campaign_id="cam_yp_seo_004",
            project="yallaplays",
            campaign_type="seo",
            title="Racing Games Category Authority",
            description=(
                "Establish category authority for racing games with dedicated pages for car racing, "
                "motorbike, kart, and drift sub-genres with video schema and review markup."
            ),
            target_keywords=["racing games", "car racing games online", "kart racing games",
                             "drift games", "speed racing games"],
            target_pages=["/games/racing", "/games/car-racing", "/games/kart"],
            estimated_impact=75.0,
            estimated_effort=EFFORT_MEDIUM,
            timeline_weeks=5,
            recommended_agents=["marketing-seo-specialist", "engineering-frontend-developer"],
            monthly_search_volume=210000,
            difficulty_score=52.0,
            priority=PRIORITY_HIGH,
        ),
        Campaign(
            campaign_id="cam_yp_seo_005",
            project="yallaplays",
            campaign_type="app_store",
            title="App Store Optimisation — YallaPlays Mobile",
            description=(
                "Full ASO audit and rewrite: title, subtitle, description, keyword field, "
                "screenshots, and preview video for improved conversion and search ranking."
            ),
            target_keywords=["free games app", "online games", "play games free", "game portal app"],
            target_pages=["/app-store-listing"],
            estimated_impact=82.0,
            estimated_effort=EFFORT_MEDIUM,
            timeline_weeks=3,
            recommended_agents=["marketing-seo-specialist", "product-manager"],
            monthly_search_volume=120000,
            difficulty_score=40.0,
            priority=PRIORITY_HIGH,
        ),
        Campaign(
            campaign_id="cam_yp_seo_006",
            project="yallaplays",
            campaign_type="content",
            title="'Best Games' Roundup Content Series",
            description=(
                "Produce 12 'Best X Games' articles targeting high-intent comparison searches "
                "across action, strategy, sports, and kids categories."
            ),
            target_keywords=["best action games", "best strategy games online", "best sports games",
                             "best free games", "best games for kids"],
            target_pages=["/blog", "/games/best"],
            estimated_impact=80.0,
            estimated_effort=EFFORT_HIGH,
            timeline_weeks=8,
            recommended_agents=["content-writer", "marketing-seo-specialist"],
            monthly_search_volume=390000,
            difficulty_score=55.0,
            priority=PRIORITY_HIGH,
        ),
        Campaign(
            campaign_id="cam_yp_seo_007",
            project="yallaplays",
            campaign_type="seo",
            title="Homepage Core Web Vitals & Technical SEO",
            description=(
                "Fix LCP, CLS, FID on homepage and category pages; implement breadcrumb schema, "
                "sitemap refresh, and canonical tag audit to remove duplicate content issues."
            ),
            target_keywords=["yallaplays", "play games online"],
            target_pages=["/", "/games", "/games/*"],
            estimated_impact=86.0,
            estimated_effort=EFFORT_MEDIUM,
            timeline_weeks=4,
            recommended_agents=["engineering-frontend-developer", "engineering-performance-optimizer",
                                 "marketing-seo-specialist"],
            monthly_search_volume=0,
            difficulty_score=30.0,
            priority=PRIORITY_HIGH,
        ),
        Campaign(
            campaign_id="cam_yp_seo_008",
            project="yallaplays",
            campaign_type="growth",
            title="Social Sharing & Viral Loop Optimisation",
            description=(
                "Add Open Graph / Twitter Card meta to all game pages, generate shareable score "
                "cards, and implement referral incentive hooks to improve organic social reach."
            ),
            target_keywords=["share games", "game score share"],
            target_pages=["/games/*", "/profile", "/leaderboard"],
            estimated_impact=72.0,
            estimated_effort=EFFORT_MEDIUM,
            timeline_weeks=4,
            recommended_agents=["marketing-seo-specialist", "engineering-frontend-developer",
                                 "product-manager"],
            monthly_search_volume=0,
            difficulty_score=35.0,
            priority=PRIORITY_MEDIUM,
        ),
    ]


def get_fionera_campaigns() -> list[Campaign]:
    return [
        Campaign(
            campaign_id="cam_fi_seo_001",
            project="fionera",
            campaign_type="seo",
            title="Investment Portfolio Tracker SEO Hub",
            description=(
                "Build SEO authority around portfolio tracking: hub page, feature pages for "
                "real-time quotes, P&L charts, and tax reporting with structured data."
            ),
            target_keywords=["portfolio tracker", "investment portfolio tracker",
                             "stock portfolio app", "free portfolio tracker"],
            target_pages=["/features/portfolio", "/features/tracking", "/pricing"],
            estimated_impact=85.0,
            estimated_effort=EFFORT_MEDIUM,
            timeline_weeks=6,
            recommended_agents=["marketing-seo-specialist", "engineering-frontend-developer"],
            monthly_search_volume=180000,
            difficulty_score=60.0,
            priority=PRIORITY_HIGH,
        ),
        Campaign(
            campaign_id="cam_fi_seo_002",
            project="fionera",
            campaign_type="content",
            title="Personal Finance & Investing Blog Launch",
            description=(
                "Launch 10-article cornerstone content series covering ETF investing, dividend "
                "tracking, and risk management to attract organic search and build trust."
            ),
            target_keywords=["how to track investments", "ETF portfolio tracker",
                             "dividend tracker app", "risk management investing"],
            target_pages=["/blog"],
            estimated_impact=78.0,
            estimated_effort=EFFORT_HIGH,
            timeline_weeks=10,
            recommended_agents=["content-writer", "marketing-seo-specialist"],
            monthly_search_volume=95000,
            difficulty_score=50.0,
            priority=PRIORITY_MEDIUM,
        ),
        Campaign(
            campaign_id="cam_fi_seo_003",
            project="fionera",
            campaign_type="app_store",
            title="Fionera App Store Optimisation",
            description=(
                "Rewrite App Store and Google Play listings with keyword-rich descriptions, "
                "new screenshots showing AI risk scoring, and localized subtitles."
            ),
            target_keywords=["stock tracker app", "portfolio manager app", "investment app"],
            target_pages=["/app-store-listing"],
            estimated_impact=80.0,
            estimated_effort=EFFORT_MEDIUM,
            timeline_weeks=3,
            recommended_agents=["marketing-seo-specialist", "product-manager"],
            monthly_search_volume=75000,
            difficulty_score=42.0,
            priority=PRIORITY_HIGH,
        ),
    ]
