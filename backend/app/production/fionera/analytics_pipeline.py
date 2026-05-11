from app.production.fionera.finance_insights import generate_finance_insights
from app.production.fionera.market_collector import collect_market_signals
from app.production.fionera.ux_optimizer import finance_ux_recommendations
from app.production.fionera.watchlist_engine import build_watchlists


def build_analytics_pipeline() -> dict:
    insights = generate_finance_insights()
    return {
        "market_signals": collect_market_signals(),
        "insights": [insight.model_dump() for insight in insights],
        "watchlists": build_watchlists(insights),
        "ux_recommendations": finance_ux_recommendations(),
        "analytics": [
            {
                "metric": "watchlist_signal_confidence",
                "recommendation": "Track average confidence by watchlist theme",
                "implementation_ready": True,
            },
            {
                "metric": "insight_engagement",
                "recommendation": "Measure clicks and saves on generated insight cards",
                "implementation_ready": True,
            },
        ],
    }
