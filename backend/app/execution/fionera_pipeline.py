from app.execution.models import ExecutionPreview
from app.production.fionera.analytics_pipeline import build_analytics_pipeline
from app.production.fionera.finance_insights import generate_finance_insights
from app.production.fionera.market_collector import collect_market_signals
from app.production.fionera.watchlist_engine import build_watchlists


def run_fionera_market_cycle() -> ExecutionPreview:
    signals = collect_market_signals()
    insights = generate_finance_insights()
    items = [
        {
            "type": "market_signal",
            **signal,
            "deployment_allowed": False,
            "destructive": False,
        }
        for signal in signals
    ] + [
        {
            "type": "finance_insight",
            **insight.model_dump(),
            "deployment_allowed": False,
            "destructive": False,
        }
        for insight in insights
    ]

    return ExecutionPreview(
        pipeline="fionera_market_cycle",
        project_id="fionera",
        summary=f"Collected {len(signals)} market signals and generated {len(insights)} insights",
        items=items,
    )


def run_fionera_watchlist_cycle() -> ExecutionPreview:
    insights = generate_finance_insights()
    watchlists = build_watchlists(insights)
    analytics = build_analytics_pipeline()["analytics"]
    items = [
        {
            "type": "watchlist",
            **watchlist,
            "deployment_allowed": False,
            "destructive": False,
        }
        for watchlist in watchlists
    ] + [
        {
            "type": "analytics",
            **item,
            "deployment_allowed": False,
            "destructive": False,
        }
        for item in analytics
    ]

    return ExecutionPreview(
        pipeline="fionera_watchlist_cycle",
        project_id="fionera",
        summary=f"Generated {len(watchlists)} watchlists and {len(analytics)} analytics previews",
        items=items,
    )
