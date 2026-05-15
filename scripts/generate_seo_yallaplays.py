"""
MIFTEH OS — YallaPlays SEO Loop
Generates: homepage SEO, category optimization, game recommendations, internal linking, mobile tips.
Output: outputs/yallaplays/seo/TIMESTAMP.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, today_str, timestamp_str

SYSTEM = (
    "You are an expert SEO specialist for YallaPlays — an online gaming platform for Arabic-speaking users in the MENA region. "
    "Generate comprehensive SEO content in JSON format. All content must be mobile-first, culturally appropriate, "
    "and optimized for MENA gaming keywords. Return only valid JSON."
)

USER = f"""Generate a complete SEO optimization package for YallaPlays for {today_str()}.

Return JSON with this exact structure:
{{
  "homepage": {{
    "title": "string — under 60 chars",
    "meta_description": "string — under 160 chars",
    "og_title": "string",
    "og_description": "string",
    "h1": "string",
    "hero_text": "string — 2 sentences",
    "keywords": ["keyword1", "keyword2"]
  }},
  "categories": [
    {{
      "slug": "action",
      "title": "string",
      "meta_description": "string",
      "h1": "string",
      "intro_text": "string"
    }}
  ],
  "top_games_to_feature": [
    {{
      "game_type": "string",
      "seo_title": "string",
      "seo_description": "string",
      "reason": "string"
    }}
  ],
  "internal_links": [
    {{
      "from_page": "string",
      "anchor_text": "string",
      "to_page": "string",
      "reason": "string"
    }}
  ],
  "mobile_optimizations": [
    {{
      "optimization": "string",
      "impact": "high",
      "implementation": "string"
    }}
  ]
}}

Include 8 categories (action, puzzle, racing, arcade, sports, adventure, strategy, shooting),
8 game recommendations, 6 internal link suggestions, 5 mobile tips."""


def _fallback():
    return {
        "homepage": {
            "title": "YallaPlays — العاب اونلاين مجانية",
            "meta_description": "العب أفضل الألعاب الإلكترونية مجاناً على YallaPlays. ألعاب أكشن، بازل، سباقات وأكثر.",
            "h1": "يلا بلاي — العاب اونلاين",
            "hero_text": "استمتع بآلاف الألعاب المجانية مباشرة في متصفحك.",
            "keywords": ["العاب اونلاين", "يلا بلاي", "العاب مجانية", "العاب عربية"],
        },
        "categories": [],
        "top_games_to_feature": [],
        "internal_links": [],
        "mobile_optimizations": [],
    }


def main():
    print("[yp-seo] Starting YallaPlays SEO generation...")
    data, tokens, cost, success = generate_json(SYSTEM, USER, model="gpt-4o-mini", max_tokens=3000)

    ts = timestamp_str()
    output = {
        "generated_at": now_iso(),
        "project": "yallaplays",
        "operation_type": "seo_page",
        "ai_generated": success,
        "ai_provider": "openai",
        "ai_model": "gpt-4o-mini",
        "tokens_used": tokens,
        "cost_usd": cost,
        "title": f"YallaPlays SEO Optimization — {today_str()}",
        "content": data if success else _fallback(),
        "pr_ready": True,
        "suggested_branch": f"ai/yp-seo-{today_str()}",
    }

    out_dir = Path("outputs/yallaplays/seo")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f"{ts}.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))
    (out_dir / "latest.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))

    status = "AI" if success else "template"
    print(f"[yp-seo] Done — {status} — {tokens} tokens — ${cost:.6f}")
    return output


if __name__ == "__main__":
    main()
