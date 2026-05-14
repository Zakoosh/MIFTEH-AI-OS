"""
roadmap_expansion.py — Strategic roadmap item generation for YallaPlays and Fionera.
"""

from __future__ import annotations

from .models import RoadmapItem, PRIORITY_HIGH, PRIORITY_MEDIUM


def get_yallaplays_roadmap() -> list[RoadmapItem]:
    return [
        RoadmapItem(
            roadmap_id="rm_yp_q3_001",
            project="yallaplays",
            quarter="Q3-2026",
            title="YallaPlays SEO & Discovery Overhaul",
            description=(
                "Full SEO and game discovery upgrade: technical SEO sprint, topical clusters "
                "for top genres, category navigation redesign, and game search with instant results."
            ),
            theme="Growth through Organic Discovery",
            work_item_ids=["wi_yp_001", "wi_yp_002", "wi_yp_003", "wi_yp_009", "wi_yp_013"],
            total_estimated_days=42,
            expected_outcomes=[
                "40% increase in organic search traffic",
                "25% improvement in category page CTR",
                "18% increase in game discovery rate",
                "Core Web Vitals all-green",
            ],
            success_metrics=[
                "Monthly organic sessions > 500k",
                "LCP < 2.5s on all category pages",
                "Category CTR > 4%",
            ],
            priority=PRIORITY_HIGH,
        ),
        RoadmapItem(
            roadmap_id="rm_yp_q3_002",
            project="yallaplays",
            quarter="Q3-2026",
            title="YallaPlays Retention & Engagement Engine",
            description=(
                "Build the retention stack: personalised recommendations, daily challenges, "
                "mobile-first game card redesign, and CDN migration for performance."
            ),
            theme="Player Retention and Daily Habits",
            work_item_ids=["wi_yp_005", "wi_yp_007", "wi_yp_010", "wi_yp_012"],
            total_estimated_days=46,
            expected_outcomes=[
                "35% increase in session depth",
                "25% increase in DAU",
                "20% improvement in mobile game launch rate",
                "40% TTFB reduction",
            ],
            success_metrics=[
                "D7 retention > 25%",
                "DAU/MAU ratio > 0.30",
                "Homepage TTFB < 400ms",
                "Avg session games played > 3",
            ],
            priority=PRIORITY_HIGH,
        ),
        RoadmapItem(
            roadmap_id="rm_yp_q4_001",
            project="yallaplays",
            quarter="Q4-2026",
            title="YallaPlays Social & Monetisation Layer",
            description=(
                "Activate social features and monetisation: leaderboards with friend challenges, "
                "achievement system, rewarded video ads, and user onboarding flow."
            ),
            theme="Social Gaming and Revenue Activation",
            work_item_ids=["wi_yp_006", "wi_yp_008", "wi_yp_011", "wi_yp_014"],
            total_estimated_days=57,
            expected_outcomes=[
                "40% increase in social sharing",
                "20% improvement in D1 retention for new users",
                "$2.5k additional monthly ad revenue",
                "20% engagement depth increase",
            ],
            success_metrics=[
                "Share rate > 5% per session",
                "D1 retention > 50%",
                "Monthly rewarded-ad revenue > $2k",
                "Achievement unlock rate > 30%",
            ],
            priority=PRIORITY_MEDIUM,
        ),
    ]


def get_fionera_roadmap() -> list[RoadmapItem]:
    return [
        RoadmapItem(
            roadmap_id="rm_fi_q3_001",
            project="fionera",
            quarter="Q3-2026",
            title="Fionera Core Intelligence Launch",
            description=(
                "Launch AI Risk Score widget, dividend tracker, multi-currency support, "
                "smart price alerts, and the premium tier — the core value proposition."
            ),
            theme="AI-Powered Portfolio Intelligence",
            work_item_ids=["wi_fi_001", "wi_fi_003", "wi_fi_004", "wi_fi_005", "wi_fi_008"],
            total_estimated_days=72,
            expected_outcomes=[
                "40% paid conversion lift from AI Risk Score",
                "30% long-term investor retention improvement",
                "International market access (20% user base growth)",
                "$50k MRR target at 3 months post-launch",
            ],
            success_metrics=[
                "AI Risk Score widget adoption > 60% of active users",
                "Multi-currency users > 30% of base",
                "MRR > $20k by end of Q3",
                "Premium conversion rate > 8%",
            ],
            priority=PRIORITY_HIGH,
        ),
        RoadmapItem(
            roadmap_id="rm_fi_q3_002",
            project="fionera",
            quarter="Q3-2026",
            title="Fionera Dashboard & Mobile UX Overhaul",
            description=(
                "Redesign dashboard, add heatmap and market overview widgets, implement dark mode, "
                "and ship the new mobile bottom navigation."
            ),
            theme="Best-in-Class User Experience",
            work_item_ids=["wi_fi_009", "wi_fi_010", "wi_fi_011", "wi_fi_016", "wi_fi_017"],
            total_estimated_days=43,
            expected_outcomes=[
                "30% improvement in daily session time",
                "15% user satisfaction score increase",
                "25% improvement in mobile session depth",
                "25% engagement increase from heatmap",
            ],
            success_metrics=[
                "Avg daily session time > 8 minutes",
                "Mobile DAU/MAU > 0.40",
                "Dark mode adoption > 45%",
                "Dashboard satisfaction NPS > 50",
            ],
            priority=PRIORITY_HIGH,
        ),
        RoadmapItem(
            roadmap_id="rm_fi_q4_001",
            project="fionera",
            quarter="Q4-2026",
            title="Fionera Social & Advanced Analytics",
            description=(
                "Add tax reporting, benchmark comparison, rebalancing alerts, watchlist sharing, "
                "performance attribution, and historical portfolio snapshots."
            ),
            theme="Advanced Analysis and Community Growth",
            work_item_ids=["wi_fi_002", "wi_fi_006", "wi_fi_007", "wi_fi_012",
                           "wi_fi_014", "wi_fi_015"],
            total_estimated_days=79,
            expected_outcomes=[
                "25% premium plan upgrade rate from tax reporting",
                "20% premium retention improvement",
                "Viral sharing loop: 20% new user acquisition",
                "Unique historical feature drives 25% premium retention",
            ],
            success_metrics=[
                "Tax report generation > 40% of premium users",
                "Benchmark comparison active usage > 50% of premium",
                "Watchlist share rate > 10%",
                "Historical snapshots viewed per session > 2",
            ],
            priority=PRIORITY_MEDIUM,
        ),
    ]
