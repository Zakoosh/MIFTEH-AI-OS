"""
MIFTEH OS — Fionera Finance Loop
Generates: market insights, watchlist optimization, UX improvements, finance widgets.
Output: outputs/fionera/insights/TIMESTAMP.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, today_str, timestamp_str

SYSTEM = (
    "You are a senior financial analyst and UX expert for Fionera — a personal finance and investment tracking app "
    "focused on the MENA region. Generate actionable insights in JSON format. Focus on practical guidance for "
    "retail investors, emerging market opportunities, and financial dashboard UX. Return only valid JSON."
)

USER = f"""Generate a comprehensive financial insights package for Fionera for {today_str()}.

Return JSON with this exact structure:
{{
  "market_insights": {{
    "summary": "string — 2-3 sentences",
    "sentiment": "bullish|neutral|bearish",
    "key_themes": ["theme1", "theme2", "theme3"],
    "sector_spotlight": {{
      "sector": "string",
      "outlook": "string",
      "reasoning": "string"
    }},
    "risk_factors": ["risk1", "risk2"],
    "opportunities": ["opp1", "opp2", "opp3"]
  }},
  "watchlist_recommendations": [
    {{
      "asset_type": "stock|etf|crypto|commodity",
      "symbol": "string",
      "name": "string",
      "reason": "string",
      "timeframe": "short|medium|long",
      "risk_level": "low|medium|high"
    }}
  ],
  "portfolio_analytics_tips": [
    {{
      "metric": "string",
      "recommendation": "string",
      "priority": "high|medium|low"
    }}
  ],
  "ux_improvements": [
    {{
      "component": "string",
      "issue": "string",
      "solution": "string",
      "impact": "high|medium|low"
    }}
  ],
  "finance_widgets": [
    {{
      "widget_name": "string",
      "description": "string",
      "visualization_type": "chart|gauge|table|ticker"
    }}
  ],
  "investment_education": {{
    "topic": "string",
    "explanation": "string",
    "key_points": ["point1", "point2"]
  }}
}}

Include 6 watchlist recommendations, 4 portfolio tips, 5 UX improvements, 4 widget suggestions."""


def _fallback():
    return {
        "market_insights": {
            "summary": "Markets remain mixed with selective opportunities in technology and energy sectors.",
            "sentiment": "neutral",
            "key_themes": ["AI adoption", "Energy transition", "MENA growth"],
            "risk_factors": ["Geopolitical uncertainty", "Rate volatility"],
            "opportunities": ["Tech sector rebound", "Saudi Vision 2030 plays"],
        },
        "watchlist_recommendations": [],
        "portfolio_analytics_tips": [],
        "ux_improvements": [],
        "finance_widgets": [],
        "investment_education": {"topic": "Portfolio Diversification", "explanation": "", "key_points": []},
    }


def main():
    print("[fi-finance] Starting Fionera finance insights generation...")
    data, tokens, cost, success = generate_json(SYSTEM, USER, model="gpt-4o-mini", max_tokens=3000)

    ts = timestamp_str()
    output = {
        "generated_at": now_iso(),
        "project": "fionera",
        "operation_type": "market_insight",
        "ai_generated": success,
        "ai_provider": "openai",
        "ai_model": "gpt-4o-mini",
        "tokens_used": tokens,
        "cost_usd": cost,
        "title": f"Fionera Market Insights — {today_str()}",
        "content": data if success else _fallback(),
        "pr_ready": True,
        "suggested_branch": f"ai/fi-insights-{today_str()}",
    }

    out_dir = Path("outputs/fionera/insights")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{ts}.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))
    (out_dir / "latest.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))

    status = "AI" if success else "template"
    print(f"[fi-finance] Done — {status} — {tokens} tokens — ${cost:.6f}")
    return output


if __name__ == "__main__":
    main()
