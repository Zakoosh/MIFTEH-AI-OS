"""
dashboard_apply.py — Dashboard improvement applier for Fionera.

Handles:
  • Dashboard layout and component improvements
  • Analytics widget additions (portfolio heatmap, market overview, etc.)
  • Watchlist configuration updates
"""

from __future__ import annotations

from typing import Any

from .models import Proposal


# ---------------------------------------------------------------------------
# Built-in Fionera proposals
# ---------------------------------------------------------------------------

FIONERA_PROPOSALS: list[dict] = [
    {
        "id": "dash_fi_001",
        "project_id": "fionera",
        "proposal_type": "dashboard",
        "title": "Improve Fionera main dashboard layout",
        "description": "Reorder dashboard sections for better information hierarchy.",
        "target_file": "src/config/dashboard.json",
        "changes": {
            "widget_title": "Portfolio Overview",
            "widget_type": "summary_card",
            "widget_position": "top-left",
            "refresh_interval": 30,
            "chart_type": "area",
            "color_scheme": "dark-blue",
        },
        "risk_level": "low",
        "tags": ["dashboard", "layout", "ux"],
    },
    {
        "id": "widget_fi_001",
        "project_id": "fionera",
        "proposal_type": "widget",
        "title": "Add portfolio heatmap widget",
        "description": "Add a new portfolio heatmap analytics widget to the Fionera dashboard.",
        "target_file": "src/config/widgets.json",
        "changes": {
            "widget_id": "portfolio_heatmap",
            "widget_name": "Portfolio Heatmap",
            "data_source": "portfolio_api",
            "display_type": "heatmap",
            "metrics": ["daily_return", "allocation", "volatility"],
            "time_range": "30d",
            "enabled": True,
        },
        "risk_level": "low",
        "tags": ["widget", "analytics", "portfolio"],
    },
    {
        "id": "widget_fi_002",
        "project_id": "fionera",
        "proposal_type": "widget",
        "title": "Add market overview widget",
        "description": "Add a market overview widget showing key indices and sector performance.",
        "target_file": "src/config/widgets.json",
        "changes": {
            "widget_id": "market_overview",
            "widget_name": "Market Overview",
            "data_source": "market_api",
            "display_type": "multi_line_chart",
            "metrics": ["sp500", "nasdaq", "dji", "vix"],
            "time_range": "7d",
            "enabled": True,
        },
        "risk_level": "low",
        "tags": ["widget", "market", "indices"],
    },
    {
        "id": "watchlist_fi_001",
        "project_id": "fionera",
        "proposal_type": "watchlist",
        "title": "Configure Fionera default watchlist",
        "description": "Set up a default watchlist with major tech stocks and ETFs.",
        "target_file": "src/config/watchlist.json",
        "changes": {
            "watchlist_name": "Tech & Growth",
            "tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "QQQ", "SPY"],
            "alert_threshold": 5.0,
            "refresh_interval": 60,
            "display_currency": "USD",
            "sort_by": "daily_change_pct",
        },
        "risk_level": "low",
        "tags": ["watchlist", "stocks", "configuration"],
    },
    {
        "id": "dash_fi_002",
        "project_id": "fionera",
        "proposal_type": "dashboard",
        "title": "Add performance analytics section",
        "description": "Add a dedicated performance analytics section with drawdown and Sharpe ratio.",
        "target_file": "src/config/dashboard.json",
        "changes": {
            "widget_title": "Performance Analytics",
            "widget_type": "analytics_panel",
            "widget_position": "bottom-right",
            "refresh_interval": 300,
            "chart_type": "combined",
            "color_scheme": "green-red",
        },
        "risk_level": "low",
        "tags": ["dashboard", "analytics", "performance"],
    },
]


# ---------------------------------------------------------------------------
# DashboardApplier
# ---------------------------------------------------------------------------

class DashboardApplier:
    """Prepares and previews dashboard change sets for Fionera."""

    def prepare_changes(self, proposal: Proposal) -> dict[str, Any]:
        """Dispatch to the appropriate handler based on proposal_type."""
        handler_map = {
            "dashboard": self._prepare_dashboard,
            "widget": self._prepare_widget,
            "watchlist": self._prepare_watchlist,
        }
        handler = handler_map.get(proposal.proposal_type, self._prepare_generic)
        return handler(proposal)

    def generate_preview_summary(self, proposal: Proposal) -> tuple[str, str]:
        before = f"[{proposal.proposal_type.upper()}] Current {proposal.proposal_type} config — {proposal.target_file}"
        after_lines = [f"  • {k}: {v}" for k, v in proposal.changes.items()]
        after = f"Proposed {proposal.proposal_type} changes:\n" + "\n".join(after_lines)
        return before, after

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _prepare_dashboard(self, proposal: Proposal) -> dict[str, Any]:
        return {
            "dashboard_update": True,
            "section": "dashboard",
            **proposal.changes,
        }

    def _prepare_widget(self, proposal: Proposal) -> dict[str, Any]:
        widget_id = proposal.changes.get("widget_id", "unknown_widget")
        return {
            "widget_added": widget_id,
            "dashboard_updated": True,
            "project": proposal.project_id,
            **proposal.changes,
        }

    def _prepare_watchlist(self, proposal: Proposal) -> dict[str, Any]:
        return {
            "watchlist_update": True,
            **proposal.changes,
        }

    def _prepare_generic(self, proposal: Proposal) -> dict[str, Any]:
        return dict(proposal.changes)

    def get_widget_result(self, proposal: Proposal) -> dict[str, Any]:
        """Build the canonical widget-added response dict."""
        widget_id = proposal.changes.get("widget_id", "unknown")
        return {
            "project": proposal.project_id,
            "widget_added": widget_id,
            "dashboard_updated": True,
        }


# Module-level singleton
dashboard_applier = DashboardApplier()


def get_builtin_proposals() -> list[dict]:
    return FIONERA_PROPOSALS
