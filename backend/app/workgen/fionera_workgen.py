"""
fionera_workgen.py — Work item catalog for Fionera.
"""

from __future__ import annotations

from .models import (
    WorkItem,
    TASK_FEATURE, TASK_IMPLEMENTATION, TASK_UX, TASK_DASHBOARD,
    TASK_ANALYTICS, TASK_WATCHLIST, TASK_WIDGET, TASK_OPTIMIZATION,
    TASK_SEO_CAMPAIGN, TASK_MONETIZATION,
    PRIORITY_CRITICAL, PRIORITY_HIGH, PRIORITY_MEDIUM, PRIORITY_LOW,
    EFFORT_LOW, EFFORT_MEDIUM, EFFORT_HIGH,
)


def get_fionera_work_items() -> list[WorkItem]:
    return [
        # ── Features ────────────────────────────────────────────────────────
        WorkItem(
            item_id="wi_fi_001",
            project="fionera",
            task_type=TASK_FEATURE,
            title="Add AI Portfolio Risk Score Widget",
            description=(
                "Build an AI-powered portfolio risk scoring widget that analyses holdings "
                "concentration, sector exposure, beta, and correlation to compute a 0–100 "
                "risk score with plain-language explanation and actionable suggestions."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=93.0,
            estimated_effort=EFFORT_HIGH,
            estimated_days=21,
            recommended_agents=["engineering-backend-developer", "data-analyst",
                                 "product-manager", "engineering-frontend-developer",
                                 "ux-designer"],
            collaboration_mission="feature-development",
            apply_proposal_type="widget",
            tags=["ai", "risk-score", "widget", "portfolio", "ml"],
            quarter="Q3-2026",
            roi_estimate="Core differentiator; drives 40% paid conversion lift",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_002",
            project="fionera",
            task_type=TASK_FEATURE,
            title="Tax Reporting & Capital Gains Calculator",
            description=(
                "Build a tax reporting module: import transactions, calculate short/long-term "
                "capital gains, generate tax-year summary PDF, support multiple countries."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=89.0,
            estimated_effort=EFFORT_HIGH,
            estimated_days=25,
            recommended_agents=["engineering-backend-developer", "product-manager",
                                 "engineering-frontend-developer"],
            collaboration_mission="feature-development",
            apply_proposal_type="feature",
            tags=["tax", "capital-gains", "pdf", "compliance"],
            quarter="Q3-2026",
            roi_estimate="Top requested feature; drives 25% premium plan upgrades",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_003",
            project="fionera",
            task_type=TASK_FEATURE,
            title="Dividend Income Tracker & Forecast",
            description=(
                "Track dividend payments per holding, show forward yield, ex-dividend dates, "
                "and generate annual income forecast chart with DRIP simulation."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=86.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=14,
            recommended_agents=["engineering-backend-developer", "data-analyst",
                                 "engineering-frontend-developer"],
            collaboration_mission="feature-development",
            apply_proposal_type="widget",
            tags=["dividends", "income", "forecast", "drip"],
            quarter="Q3-2026",
            roi_estimate="~30% increase in long-term investor retention",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_004",
            project="fionera",
            task_type=TASK_FEATURE,
            title="Multi-Currency Portfolio Support",
            description=(
                "Support holdings in multiple currencies with real-time FX conversion, "
                "base currency selection, and P&L shown in both local and base currency."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=84.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=12,
            recommended_agents=["engineering-backend-developer", "engineering-frontend-developer",
                                 "product-manager"],
            collaboration_mission="feature-development",
            apply_proposal_type="feature",
            tags=["multi-currency", "fx", "international", "portfolio"],
            quarter="Q3-2026",
            roi_estimate="Unlocks international markets, projected 20% user base growth",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_005",
            project="fionera",
            task_type=TASK_FEATURE,
            title="Smart Price Alert System",
            description=(
                "Build rule-based price alerts: percentage change, absolute threshold, "
                "52-week high/low breach. Push + email delivery with snooze and bulk management."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=83.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=10,
            recommended_agents=["engineering-backend-developer", "engineering-frontend-developer"],
            collaboration_mission="feature-development",
            apply_proposal_type="watchlist",
            tags=["alerts", "notifications", "price", "push"],
            quarter="Q3-2026",
            roi_estimate="~35% improvement in daily active usage",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_006",
            project="fionera",
            task_type=TASK_FEATURE,
            title="Portfolio Benchmark Comparison",
            description=(
                "Allow users to benchmark their portfolio against S&P 500, NASDAQ, custom ETFs, "
                "and other users (anonymised). Show alpha, beta, and Sharpe ratio."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=81.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=12,
            recommended_agents=["data-analyst", "engineering-backend-developer",
                                 "engineering-frontend-developer"],
            collaboration_mission="feature-development",
            apply_proposal_type="widget",
            tags=["benchmark", "alpha", "sharpe", "comparison"],
            quarter="Q4-2026",
            roi_estimate="~20% increase in premium plan retention",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_007",
            project="fionera",
            task_type=TASK_FEATURE,
            title="Automated Rebalancing Alerts",
            description=(
                "Detect portfolio drift from target allocation and send rebalancing "
                "recommendations with exact buy/sell amounts per asset."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=80.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=11,
            recommended_agents=["engineering-backend-developer", "data-analyst",
                                 "product-manager"],
            collaboration_mission="feature-development",
            apply_proposal_type="feature",
            tags=["rebalancing", "allocation", "automation", "alerts"],
            quarter="Q4-2026",
            roi_estimate="~25% improvement in portfolio management engagement",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_008",
            project="fionera",
            task_type=TASK_MONETIZATION,
            title="Premium Tier Launch — Pro & Institutional",
            description=(
                "Define and launch Pro ($9.99/mo) and Institutional ($49.99/mo) tiers. "
                "Pro: unlimited watchlists, tax reports, AI risk score. "
                "Institutional: API access, team portfolios, white-label."
            ),
            priority=PRIORITY_CRITICAL,
            estimated_impact=95.0,
            estimated_effort=EFFORT_HIGH,
            estimated_days=28,
            recommended_agents=["product-manager", "engineering-backend-developer",
                                 "engineering-frontend-developer", "marketing-seo-specialist"],
            collaboration_mission="monetization-strategy",
            apply_proposal_type="feature",
            tags=["premium", "monetisation", "saas", "institutional"],
            quarter="Q3-2026",
            roi_estimate="Primary revenue driver; target $50k MRR at 3 months post-launch",
            source="fionera_workgen",
        ),

        # ── Dashboard / Widgets ─────────────────────────────────────────────
        WorkItem(
            item_id="wi_fi_009",
            project="fionera",
            task_type=TASK_DASHBOARD,
            title="Portfolio Overview Dashboard Redesign",
            description=(
                "Redesign the main dashboard: add net worth card, sector allocation donut, "
                "P&L sparklines per holding, and a today's movers strip."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=87.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=12,
            recommended_agents=["ux-designer", "engineering-frontend-developer", "product-manager"],
            collaboration_mission="dashboard-improvement",
            apply_proposal_type="dashboard",
            tags=["dashboard", "redesign", "portfolio", "ux"],
            quarter="Q3-2026",
            roi_estimate="~30% improvement in daily session time",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_010",
            project="fionera",
            task_type=TASK_WIDGET,
            title="Portfolio Heatmap Widget",
            description=(
                "Build an interactive heatmap widget showing all holdings coloured by daily "
                "performance. Cell size = portfolio weight. Click to drill into a holding."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=82.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=9,
            recommended_agents=["engineering-frontend-developer", "ux-designer", "data-analyst"],
            collaboration_mission="dashboard-improvement",
            apply_proposal_type="widget",
            tags=["heatmap", "widget", "visualisation", "holdings"],
            quarter="Q3-2026",
            roi_estimate="~25% increase in dashboard engagement time",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_011",
            project="fionera",
            task_type=TASK_WIDGET,
            title="Market Overview Widget",
            description=(
                "Add a Market Overview widget showing major indices (S&P 500, NASDAQ, FTSE, "
                "Nikkei), commodities (Gold, Oil), and crypto (BTC, ETH) with 24h change."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=76.0,
            estimated_effort=EFFORT_LOW,
            estimated_days=5,
            recommended_agents=["engineering-frontend-developer", "engineering-backend-developer"],
            collaboration_mission="dashboard-improvement",
            apply_proposal_type="widget",
            tags=["market-overview", "widget", "indices", "macro"],
            quarter="Q3-2026",
            roi_estimate="Contextual data increases stickiness by ~15%",
            source="fionera_workgen",
        ),

        # ── Watchlist ───────────────────────────────────────────────────────
        WorkItem(
            item_id="wi_fi_012",
            project="fionera",
            task_type=TASK_WATCHLIST,
            title="Watchlist Sharing & Social Discovery",
            description=(
                "Allow users to share watchlists publicly or with followers. "
                "Add a curated 'Top Watchlists' discovery feed with follow and clone actions."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=78.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=11,
            recommended_agents=["engineering-backend-developer", "engineering-frontend-developer",
                                 "product-manager"],
            collaboration_mission="feature-development",
            apply_proposal_type="watchlist",
            tags=["watchlist", "social", "sharing", "discovery"],
            quarter="Q4-2026",
            roi_estimate="Viral growth loop; ~20% new user acquisition from shares",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_013",
            project="fionera",
            task_type=TASK_WATCHLIST,
            title="Smart Watchlist — AI-Powered Stock Suggestions",
            description=(
                "Analyse user watchlists and portfolio to suggest correlated, complementary, "
                "or trending stocks using ML-based similarity scoring."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=80.0,
            estimated_effort=EFFORT_HIGH,
            estimated_days=18,
            recommended_agents=["data-analyst", "engineering-backend-developer",
                                 "product-manager"],
            collaboration_mission="feature-development",
            apply_proposal_type="watchlist",
            tags=["watchlist", "ai", "suggestions", "ml"],
            quarter="Q4-2026",
            roi_estimate="~30% increase in watchlist depth per user",
            source="fionera_workgen",
        ),

        # ── Analytics ───────────────────────────────────────────────────────
        WorkItem(
            item_id="wi_fi_014",
            project="fionera",
            task_type=TASK_ANALYTICS,
            title="Performance Attribution Analytics",
            description=(
                "Build attribution analysis: break down portfolio return into sector, "
                "geographic, and individual stock contribution with waterfall chart."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=84.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=13,
            recommended_agents=["data-analyst", "engineering-frontend-developer",
                                 "engineering-backend-developer"],
            collaboration_mission="feature-development",
            apply_proposal_type="widget",
            tags=["attribution", "analytics", "waterfall", "performance"],
            quarter="Q4-2026",
            roi_estimate="~20% retention improvement for active traders",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_015",
            project="fionera",
            task_type=TASK_ANALYTICS,
            title="Historical Portfolio Snapshots & Time Travel",
            description=(
                "Allow users to view their portfolio as it was on any past date. "
                "Store daily snapshots and render historical allocation, value, and returns."
            ),
            priority=PRIORITY_MEDIUM,
            estimated_impact=79.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=10,
            recommended_agents=["engineering-backend-developer", "data-analyst",
                                 "engineering-frontend-developer"],
            collaboration_mission="feature-development",
            apply_proposal_type="feature",
            tags=["history", "snapshots", "time-travel", "analytics"],
            quarter="Q4-2026",
            roi_estimate="Unique feature; drives ~25% premium retention",
            source="fionera_workgen",
        ),

        # ── UX ───────────────────────────────────────────────────────────────
        WorkItem(
            item_id="wi_fi_016",
            project="fionera",
            task_type=TASK_UX,
            title="Dark Mode & Theming System",
            description=(
                "Implement full dark mode with system-preference detection and manual toggle. "
                "Build a design token system for consistent theming across all components."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=77.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=8,
            recommended_agents=["ux-designer", "engineering-frontend-developer"],
            collaboration_mission="dashboard-improvement",
            apply_proposal_type="dashboard",
            tags=["dark-mode", "theming", "design-tokens", "ux"],
            quarter="Q3-2026",
            roi_estimate="High user demand; expected 15% satisfaction score increase",
            source="fionera_workgen",
        ),
        WorkItem(
            item_id="wi_fi_017",
            project="fionera",
            task_type=TASK_UX,
            title="Mobile App Redesign — Bottom Navigation",
            description=(
                "Redesign mobile navigation: replace hamburger with bottom tab bar. "
                "Tabs: Portfolio, Watchlist, Markets, Alerts, Profile."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=81.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=9,
            recommended_agents=["ux-designer", "engineering-frontend-developer",
                                 "product-manager"],
            collaboration_mission="dashboard-improvement",
            apply_proposal_type="dashboard",
            tags=["mobile", "navigation", "bottom-bar", "ux"],
            quarter="Q3-2026",
            roi_estimate="~25% improvement in mobile session depth",
            source="fionera_workgen",
        ),

        # ── SEO ──────────────────────────────────────────────────────────────
        WorkItem(
            item_id="wi_fi_018",
            project="fionera",
            task_type=TASK_SEO_CAMPAIGN,
            title="Investment Portfolio Tracker SEO Hub",
            description=(
                "Build SEO authority around portfolio tracking: hub page, feature pages, "
                "structured data for SaaS, and FAQ schema for comparison queries."
            ),
            priority=PRIORITY_HIGH,
            estimated_impact=85.0,
            estimated_effort=EFFORT_MEDIUM,
            estimated_days=10,
            recommended_agents=["marketing-seo-specialist", "engineering-frontend-developer"],
            collaboration_mission="seo-growth",
            apply_proposal_type="seo",
            tags=["seo", "portfolio-tracker", "hub", "schema"],
            quarter="Q3-2026",
            roi_estimate="~35% increase in organic trial signups",
            source="fionera_workgen",
        ),
    ]
