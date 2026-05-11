def mobile_ux_recommendations() -> list[dict]:
    return [
        {
            "area": "touch_controls",
            "recommendation": "Add large thumb-zone play buttons and pause controls for mobile sessions",
            "mobile_score": 84,
            "implementation_ready": True,
        },
        {
            "area": "game_cards",
            "recommendation": "Use two-column mobile game cards with lazy-loaded thumbnails",
            "mobile_score": 88,
            "implementation_ready": True,
        },
        {
            "area": "performance",
            "recommendation": "Preload first playable game asset and defer non-critical widgets",
            "mobile_score": 82,
            "implementation_ready": True,
        },
    ]
