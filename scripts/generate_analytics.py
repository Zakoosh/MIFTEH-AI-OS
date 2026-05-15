"""
MIFTEH OS — Analytics Loop
Generates weekly performance analysis and AI system reports.
Output: outputs/mifteh/analytics/TIMESTAMP.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, today_str, timestamp_str

SYSTEM = (
    "You are a business analytics AI generating performance reports for MIFTEH AI OS and its three products. "
    "Generate concise, actionable weekly summaries in JSON format. Return only valid JSON."
)

USER = f"""Generate a weekly analytics and strategy summary for the week ending {today_str()}.

Return JSON with this structure:
{{
  "executive_summary": "string — 2-3 sentences",
  "yallaplays": {{
    "seo_score_estimate": 72,
    "top_opportunities": ["opp1", "opp2", "opp3"],
    "content_recommendations": ["rec1", "rec2"],
    "growth_tactics": ["tactic1", "tactic2"]
  }},
  "fionera": {{
    "user_engagement_insights": "string",
    "feature_priorities": ["feature1", "feature2"],
    "market_opportunities": ["opp1", "opp2"]
  }},
  "mifteh": {{
    "positioning_insights": "string",
    "content_gaps": ["gap1", "gap2"],
    "growth_opportunities": ["opp1", "opp2"]
  }},
  "ai_performance": {{
    "effectiveness_notes": "string",
    "optimization_suggestions": ["sug1", "sug2"]
  }},
  "next_week_priorities": ["priority1", "priority2", "priority3"]
}}"""


def main():
    print("[analytics] Starting analytics generation...")
    data, tokens, cost, success = generate_json(SYSTEM, USER, model="gpt-4o-mini", max_tokens=2000)

    ts = timestamp_str()
    output = {
        "generated_at": now_iso(),
        "project": "mifteh",
        "operation_type": "analytics_report",
        "ai_generated": success,
        "ai_provider": "openai",
        "ai_model": "gpt-4o-mini",
        "tokens_used": tokens,
        "cost_usd": cost,
        "title": f"Weekly Analytics Report — {today_str()}",
        "content": data if success else {},
        "pr_ready": False,
    }

    out_dir = Path("outputs/mifteh/analytics")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{ts}.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))
    (out_dir / "latest.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))

    memory_dir = Path("memory")
    memory_dir.mkdir(exist_ok=True)
    (memory_dir / "analytics_latest.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))

    status = "AI" if success else "template"
    print(f"[analytics] Done — {status} — {tokens} tokens — ${cost:.6f}")
    return output


if __name__ == "__main__":
    main()
