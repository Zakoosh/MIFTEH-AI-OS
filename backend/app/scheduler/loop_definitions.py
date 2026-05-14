from __future__ import annotations

# All loop definitions. interval_minutes controls APScheduler trigger frequency.
YALLAPLAYS_LOOPS = [
    {
        "id": "yp_seo",
        "project": "yallaplays",
        "label": "SEO Generation",
        "operation_type": "seo_page",
        "topic": "",
        "interval_minutes": 360,   # every 6h
        "priority": 1,
    },
    {
        "id": "yp_metadata",
        "project": "yallaplays",
        "label": "Metadata Optimization",
        "operation_type": "metadata_patch",
        "topic": "",
        "interval_minutes": 1440,  # every 24h
        "priority": 2,
    },
    {
        "id": "yp_category",
        "project": "yallaplays",
        "label": "Category Optimization",
        "operation_type": "category_page",
        "topic": "",
        "interval_minutes": 720,   # every 12h
        "priority": 2,
    },
    {
        "id": "yp_linking",
        "project": "yallaplays",
        "label": "Internal Linking",
        "operation_type": "internal_linking",
        "topic": "",
        "interval_minutes": 1440,  # every 24h
        "priority": 3,
    },
    {
        "id": "yp_recommendations",
        "project": "yallaplays",
        "label": "Homepage Recommendations",
        "operation_type": "game_recommendation",
        "topic": "",
        "interval_minutes": 360,   # every 6h
        "priority": 2,
    },
    {
        "id": "yp_mobile",
        "project": "yallaplays",
        "label": "Mobile Optimization",
        "operation_type": "mobile_optimization",
        "topic": "",
        "interval_minutes": 1440,  # every 24h
        "priority": 3,
    },
]

FIONERA_LOOPS = [
    {
        "id": "fi_insights",
        "project": "fionera",
        "label": "Finance Insights",
        "operation_type": "market_insight",
        "topic": "",
        "interval_minutes": 720,   # every 12h
        "priority": 1,
    },
    {
        "id": "fi_market",
        "project": "fionera",
        "label": "Market Analysis",
        "operation_type": "finance_widget",
        "topic": "",
        "interval_minutes": 720,   # every 12h
        "priority": 1,
    },
    {
        "id": "fi_watchlist",
        "project": "fionera",
        "label": "Watchlist Optimization",
        "operation_type": "watchlist_improvement",
        "topic": "",
        "interval_minutes": 1440,  # every 24h
        "priority": 2,
    },
    {
        "id": "fi_analytics",
        "project": "fionera",
        "label": "Analytics Generation",
        "operation_type": "analytics_dashboard",
        "topic": "",
        "interval_minutes": 1440,  # every 24h
        "priority": 2,
    },
    {
        "id": "fi_ux",
        "project": "fionera",
        "label": "UX Optimization",
        "operation_type": "ux_proposal",
        "topic": "",
        "interval_minutes": 1440,  # every 24h
        "priority": 3,
    },
]

MIFTEH_LOOPS = [
    {
        "id": "mi_seo",
        "label": "SEO Generation",
        "project": "mifteh",
        "output_type": "seo_page",
        "topic": "AI Operations",
        "interval_minutes": 720,
    },
    {
        "id": "mi_content",
        "label": "Content Optimization",
        "project": "mifteh",
        "output_type": "metadata_patch",
        "topic": "",
        "interval_minutes": 1440,
    },
    {
        "id": "mi_ux",
        "label": "UX Proposals",
        "project": "mifteh",
        "output_type": "ux_proposal",
        "topic": "",
        "interval_minutes": 1440,
    },
]

ALL_LOOPS = YALLAPLAYS_LOOPS + FIONERA_LOOPS + MIFTEH_LOOPS

LOOP_INDEX = {loop["id"]: loop for loop in ALL_LOOPS}
