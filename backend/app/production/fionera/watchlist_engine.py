def build_watchlists(insights: list) -> list[dict]:
    return [
        {
            "name": "AI Infrastructure Leaders",
            "symbols": [item.symbol for item in insights if item.symbol in {"NVDA", "MSFT"}],
            "reason": "Track companies with durable AI infrastructure demand",
            "implementation_ready": True,
        },
        {
            "name": "High Volatility Watch",
            "symbols": [item.symbol for item in insights if item.trend == "volatile"],
            "reason": "Surface risk bands and position sizing warnings",
            "implementation_ready": True,
        },
    ]
