from app.production.fionera.market_collector import collect_market_signals
from app.production.models import FioneraInsight


def generate_finance_insights() -> list[FioneraInsight]:
    insights = []
    for signal in collect_market_signals():
        symbol = signal["symbol"]
        trend = signal["trend"]
        insights.append(FioneraInsight(
            symbol=symbol,
            trend=trend,
            recommended_watchlist=trend in {"bullish", "volatile"},
            insight=(
                "AI infrastructure momentum remains strong"
                if symbol == "NVDA"
                else signal["signal"]
            ),
            confidence=signal["confidence"],
            actions=[
                "Add to thematic watchlist",
                "Track trend and volatility bands",
                "Generate dashboard insight card",
            ],
        ))
    return insights
