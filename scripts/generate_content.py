"""
MIFTEH OS — Content Generation Loop
Generates content optimization suggestions for all three projects.
Output: outputs/{project}/content/TIMESTAMP.json
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, today_str, timestamp_str

SYSTEM = (
    "You are a content strategist for MIFTEH AI OS, generating content optimization suggestions for three products: "
    "YallaPlays (MENA gaming platform), Fionera (personal finance app), and Mifteh.com (AI OS platform). "
    "Generate actionable, specific content improvements in JSON format. Return only valid JSON."
)

USER = f"""Generate content optimization suggestions for all three products for {today_str()}.

Return JSON with this structure:
{{
  "yallaplays": {{
    "blog_post_ideas": [
      {{"title": "string", "keyword": "string", "word_count": 800, "outline": ["section1", "section2"]}}
    ],
    "game_descriptions": [
      {{"genre": "string", "template_description": "string", "keywords": ["kw1"]}}
    ],
    "social_content": [
      {{"platform": "instagram", "content": "string", "hashtags": ["#tag"]}}
    ]
  }},
  "fionera": {{
    "educational_content": [
      {{"topic": "string", "format": "article|infographic", "key_points": ["point1"]}}
    ],
    "feature_announcements": [
      {{"feature": "string", "user_benefit": "string", "announcement_copy": "string"}}
    ]
  }},
  "mifteh": {{
    "thought_leadership": [
      {{"topic": "string", "angle": "string", "key_argument": "string", "cta": "string"}}
    ],
    "product_copy": [
      {{"section": "string", "improved_copy": "string", "reason": "string"}}
    ]
  }}
}}

Include 3 blog ideas, 3 game descriptions, 2 social posts for YallaPlays;
2 educational pieces, 2 feature announcements for Fionera;
2 thought leadership pieces, 3 product copy improvements for Mifteh."""


def main():
    print("[content] Starting content generation for all projects...")
    data, tokens, cost, success = generate_json(SYSTEM, USER, model="gpt-4o-mini", max_tokens=3000)

    ts = timestamp_str()

    for project in ["yallaplays", "fionera", "mifteh"]:
        project_data = (data or {}).get(project, {})
        output = {
            "generated_at": now_iso(),
            "project": project,
            "operation_type": "content_optimization",
            "ai_generated": success,
            "ai_provider": "openai",
            "ai_model": "gpt-4o-mini",
            "tokens_used": tokens // 3,
            "cost_usd": round(cost / 3, 8),
            "title": f"{project.title()} Content Strategy — {today_str()}",
            "content": project_data,
            "pr_ready": True,
            "suggested_branch": f"ai/{project[:2]}-content-{today_str()}",
        }
        out_dir = Path(f"outputs/{project}/content")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{ts}.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))
        (out_dir / "latest.json").write_text(json.dumps(output, indent=2, ensure_ascii=False))

    status = "AI" if success else "template"
    print(f"[content] Done — {status} — {tokens} tokens — ${cost:.6f}")


if __name__ == "__main__":
    main()
