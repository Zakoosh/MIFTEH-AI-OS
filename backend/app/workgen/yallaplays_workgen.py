"""
yallaplays_workgen.py — Work item catalog for YallaPlays.
"""

from __future__ import annotations

from .models import (
    WorkItem,
    TASK_SEO_CAMPAIGN, TASK_FEATURE, TASK_IMPLEMENTATION, TASK_UX,
    TASK_OPTIMIZATION, TASK_CONTENT, TASK_MONETIZATION, TASK_CAMPAIGN,
    PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW,
    EFFORT_LOW, EFFORT_MEDIUM, EFFORT_HIGH,
)


def get_yallaplays_work_items() -> list[WorkItem]:
    return [
        # ── SEO / Campaign ─────────────────────────────────────────────────
        WorkItem(
            item_id="wi_yp_001",
            project="yallaplays",
            task_type=TASK_SEO_CAMPAIGN,
            title="Build Survival Games SEO Cluster",
            description=(
                "Create topical authority around survival games with a hub page, sub-genre "
                "landing pages (battle royale, crafting, zombie), internal linking strategy, "
                "and JSON-LD schema markup for GameApplication."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=88.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=10,
            recommended_agents=["marketing-seo-specialist", "engineering-frontend-developer"],
            collaboration_mission="seo-growth",
            apply_proposal_type="seo",
            tags=["seo", "survival", "cluster", "schema"],
            quarter="Q3-2026",
            roi_estimate="~30% organic traffic increase for survival game queries",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_002",
            project="yallaplays",
            task_type=TASK_SEO_CAMPAIGN,
            title="Multiplayer Games Discovery Hub",
            description=(
                "Build a hub page for multiplayer games with player-count filters, game type "
                "badges, and rich snippets. Targets 'multiplayer games' and related long-tail keywords."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=85.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=8,
            recommended_agents=["marketing-seo-specialist", "engineering-frontend-developer",
                                 "product-manager"],
            collaboration_mission="seo-growth",
            apply_proposal_type="seo",
            tags=["seo", "multiplayer", "discovery", "hub"],
            quarter="Q3-2026",
            roi_estimate="~25% increase in multiplayer category page traffic",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_003",
            project="yallaplays",
            task_type=TASK_SEO_CAMPAIGN,
            title="Core Web Vitals & Technical SEO Sprint",
            description=(
                "Fix LCP, CLS, and FID scores on homepage and top 20 category pages. "
                "Implement breadcrumb schema, refresh sitemap, audit canonical tags."
            ),
            priority=PRIORITY_CRITICAL,
            estimated_impact=86.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=7,
            recommended_agents=["engineering-frontend-developer",
                                 "engineering-performance-optimizer", "marketing-seo-specialist"],
            collaboration_mission="seo-growth",
            apply_proposal_type="seo",
            tags=["cwv", "technical-seo", "performance", "canonical"],
            quarter="Q3-2026",
            roi_estimate="Recover estimated 15% traffic lost to Core Web Vitals penalties",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_004",
            project="yallaplays",
            task_type=TASK_CAMPAIGN,
            title="App Store Optimisation — YallaPlays Mobile",
            description=(
                "Full ASO audit: rewrite title, subtitle, keyword field, screenshots, and preview "
                "video for both App Store and Google Play to improve conversion and search ranking."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=82.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=6,
            recommended_agents=["marketing-seo-specialist", "product-manager"],
            collaboration_mission="category-optimization",
            apply_proposal_type="metadata",
            tags=["aso", "app-store", "mobile", "conversion"],
            quarter="Q3-2026",
            roi_estimate="~20% app install rate improvement",
            source="yallaplays_workgen",
        ),

        # ── Features ────────────────────────────────────────────────────────
        WorkItem(
            item_id="wi_yp_005",
            project="yallaplays",
            task_type=TASK_FEATURE,
            title="Personalised Game Recommendations Engine",
            description=(
                "Build a recommendation engine using play history and genre preferences to surface "
                "relevant games on the homepage and post-game screen. Uses collaborative filtering."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=91.0,
            estimated_effort=EFFORT_HIGH,
            estimated_days=21,
            recommended_agents=["engineering-backend-developer", "data-analyst",
                                 "product-manager", "engineering-frontend-developer"],
            collaboration_mission="feature-development",
            apply_proposal_type="feature",
            tags=["recommendations", "personalisation", "ml", "retention"],
            quarter="Q3-2026",
            roi_estimate="~35% increase in session depth and return visits",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_006",
            project="yallaplays",
            task_type=TASK_FEATURE,
            title="Global Leaderboards with Friend Challenges",
            description=(
                "Implement per-game global and friend leaderboards. Add challenge mechanic "
                "(beat my score) with push notifications and social share cards."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=84.0,
            estimated_effort=EFFORT_HIGH,
            estimated_days=18,
            recommended_agents=["engineering-backend-developer", "engineering-frontend-developer",
                                 "product-manager"],
            collaboration_mission="feature-development",
            apply_proposal_type="feature",
            tags=["leaderboard", "social", "gamification", "retention"],
            quarter="Q3-2026",
            roi_estimate="~40% increase in social sharing and repeat play",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_007",
            project="yallaplays",
            task_type=TASK_FEATURE,
            title="Daily Challenge Mode",
            description=(
                "Add a Daily Challenge feature with a fresh curated game each day, time-limited "
                "scoring, and a streak reward system to drive daily active users."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=87.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=12,
            recommended_agents=["product-manager", "engineering-backend-developer",
                                 "engineering-frontend-developer"],
            collaboration_mission="feature-development",
            apply_proposal_type="feature",
            tags=["daily-challenge", "streak", "dau", "gamification"],
            quarter="Q3-2026",
            roi_estimate="~25% DAU increase, improved D7 retention",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_008",
            project="yallaplays",
            task_type=TASK_FEATURE,
            title="In-Game Achievement System",
            description=(
                "Design and implement a cross-game achievement system: badges, unlockables, "
                "and a trophy room in the user profile to increase engagement depth."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=79.0,
            estimated_effort=EFFORT_HIGH,
            estimated_days=20,
            recommended_agents=["product-manager", "engineering-backend-developer",
                                 "engineering-frontend-developer", "ux-designer"],
            collaboration_mission="feature-development",
            apply_proposal_type="feature",
            tags=["achievements", "badges", "profile", "engagement"],
            quarter="Q4-2026",
            roi_estimate="~20% increase in session length",
            source="yallaplays_workgen",
        ),

        # ── UX ───────────────────────────────────────────────────────────────
        WorkItem(
            item_id="wi_yp_009",
            project="yallaplays",
            task_type=TASK_UX,
            title="Redesign Game Category Navigation",
            description=(
                "Redesign the category navigation with mega-menu, visual genre icons, and "
                "quick-filter chips. A/B test against current flat navigation."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=80.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=10,
            recommended_agents=["ux-designer", "engineering-frontend-developer", "product-manager"],
            collaboration_mission="category-optimization",
            apply_proposal_type="landing_page",
            tags=["navigation", "ux", "category", "a-b-test"],
            quarter="Q3-2026",
            roi_estimate="~15% improvement in category page CTR",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_010",
            project="yallaplays",
            task_type=TASK_UX,
            title="Mobile-First Game Card Redesign",
            description=(
                "Redesign game cards for mobile: larger thumbnails, one-tap launch, "
                "inline rating stars, and offline indicator badge."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=83.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=8,
            recommended_agents=["ux-designer", "engineering-frontend-developer"],
            collaboration_mission="category-optimization",
            apply_proposal_type="landing_page",
            tags=["mobile", "game-card", "ux", "tap-to-play"],
            quarter="Q3-2026",
            roi_estimate="~20% improvement in mobile game launch rate",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_011",
            project="yallaplays",
            task_type=TASK_UX,
            title="Onboarding Flow for New Users",
            description=(
                "Build a 3-step onboarding: genre selection, favourite game picks, "
                "and push notification opt-in with contextual permission rationale."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=77.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=9,
            recommended_agents=["ux-designer", "product-manager", "engineering-frontend-developer"],
            collaboration_mission="feature-development",
            apply_proposal_type="landing_page",
            tags=["onboarding", "new-user", "personalisation", "push"],
            quarter="Q4-2026",
            roi_estimate="~30% improvement in D1 retention for new installs",
            source="yallaplays_workgen",
        ),

        # ── Implementation / Optimization ──────────────────────────────────
        WorkItem(
            item_id="wi_yp_012",
            project="yallaplays",
            task_type=TASK_IMPLEMENTATION,
            title="CDN Migration for Game Assets",
            description=(
                "Migrate all static game assets (images, JS bundles) to a global CDN with "
                "edge caching and Brotli compression to reduce TTFB by 40%."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=85.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=7,
            recommended_agents=["engineering-backend-developer",
                                 "engineering-performance-optimizer"],
            collaboration_mission="performance-optimization",
            apply_proposal_type="implementation",
            tags=["cdn", "performance", "assets", "ttfb"],
            quarter="Q3-2026",
            roi_estimate="40% TTFB reduction, 10% SEO ranking boost",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_013",
            project="yallaplays",
            task_type=TASK_IMPLEMENTATION,
            title="Game Search with Instant Results",
            description=(
                "Implement a full-text search with instant suggestions using ElasticSearch or "
                "Typesense. Support fuzzy matching, genre filters, and trending boosts."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=82.0,
            estimated_effort=EFFORT_HIGH,
            estimated_days=16,
            recommended_agents=["engineering-backend-developer", "engineering-frontend-developer",
                                 "product-manager"],
            collaboration_mission="feature-development",
            apply_proposal_type="implementation",
            tags=["search", "instant", "typesense", "discovery"],
            quarter="Q3-2026",
            roi_estimate="~18% increase in game discovery rate",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_014",
            project="yallaplays",
            task_type=TASK_MONETIZATION,
            title="Rewarded Video Ads Integration",
            description=(
                "Integrate rewarded video ad network. Players watch a 30-second ad to unlock "
                "extra lives or power-ups. Revenue share model with 70/30 split."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=76.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=10,
            recommended_agents=["engineering-mobile-developer", "product-manager",
                                 "marketing-seo-specialist"],
            collaboration_mission="monetization-strategy",
            apply_proposal_type="implementation",
            tags=["monetisation", "ads", "rewarded-video", "revenue"],
            quarter="Q4-2026",
            roi_estimate="~$2.5k additional monthly revenue",
            source="yallaplays_workgen",
        ),
        WorkItem(
            item_id="wi_yp_015",
            project="yallaplays",
            task_type=TASK_OPTIMIZATION,
            title="Homepage Landing Page A/B Test — Hero Section",
            description=(
                "Run an A/B test on three hero section variants: game montage video vs. "
                "interactive demo vs. top-trending games grid. Track D1 retention and session depth."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=74.0,
            estimated_effort=EFFORT_LOW,
            estimated_days=5,
            recommended_agents=["product-manager", "ux-designer", "data-analyst"],
            collaboration_mission="dashboard-improvement",
            apply_proposal_type="landing_page",
            tags=["a-b-test", "hero", "homepage", "conversion"],
            quarter="Q3-2026",
            roi_estimate="Expected 10–15% conversion lift based on variant performance",
            source="yallaplays_workgen",
        ),
    ]
