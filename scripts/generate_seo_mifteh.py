"""
MIFTEH OS — Mifteh.com SEO Loop
Generates: homepage SEO, landing page optimization, content strategy.
Output: outputs/mifteh/seo/TIMESTAMP.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, today_str, timestamp_str

SYSTEM = (
    "You are a digital marketing and SEO consultant for MIFTEH — an AI-powered operating system and automation platform. "
    "Generate SEO and landing page optimization recommendations in JSON format. Target tech-savvy B2B/B2C users "
    "in the MENA region interested in AI tools and automation. Return only valid JSON."
)

USER = f"""Generate a comprehensive SEO and content package for miftehos.com for {today_str()}.

Return JSON with this exact structure:
{{
  "homepage_seo": {{
    "title": "string — under 60 chars",
    "meta_description": "string — under 160 chars",
    "og_title": "string",
    "og_description": "string",
    "h1": "string",
    "hero_headline": "string — punchy, conversion-focused",
    "hero_subtext": "string — 1-2 sentences",
    "keywords": ["keyword1", "keyword2"]
  }},
  "landing_page_improvements": [
    {{
      "section": "string",
      "current_issue": "string",
      "improvement": "string",
      "expected_impact": "string"
    }}
  ],
  "content_recommendations": [
    {{
      "content_type": "blog|case-study|feature-page|comparison",
      "title": "string",
      "target_keyword": "string",
      "outline": ["section1", "section2"],
      "priority": "high|medium|low"
    }}
  ],
  "technical_seo": [
    {{
      "action": "string",
      "priority": "high|medium|low",
      "reason": "string"
    }}
  ],
  "cta_optimization": {{
    "primary_cta": "string",
    "secondary_cta": "string",
    "placement_tips": ["tip1", "tip2"]
  }}
}}

Include 5 landing page improvements, 4 content recommendations, 4 technical SEO actions."""


def main():
    print("[mi-seo] Starting Mifteh SEO generation...")
    data, tokens, cost, success = generate_json(SYSTEM, USER, model="gpt-4o-mini", max_tokens=2500)

    ts = timestamp_str()
    output = {
        "generated_at": now_iso(),
        "project": "mifteh",
        "operation_type": "seo_page",
        "ai_generated": success,
        "ai_provider": "openai",
        "ai_model": "gpt-4o-mini",
        "tokens_used": tokens,
        "cost_usd": cost,
        "title": f"Mifteh.com SEO Optimization — {today_str()}",
        "content": data if success else {},
        "pr_ready": True,
        "suggested_branch": f"ai/mi-seo-{today_str()}",
    }

    out_dir = Path("outputs/mifteh/seo")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{ts}.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))
    (out_dir / "latest.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))

    status = "AI" if success else "template"
    print(f"[mi-seo] Done — {status} — {tokens} tokens — ${cost:.6f}")
    return output


if __name__ == "__main__":
    main()
