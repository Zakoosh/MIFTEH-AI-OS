"""
MIFTEH OS — Product Roadmap Engine
AI-driven gap detection across all 3 projects.
Detects: missing features, SEO gaps, UX gaps, monetization opportunities,
engagement opportunities. Generates a prioritized roadmap.json + decision queue.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, timestamp_str
from memory_engine import get_memory_context, get_all_strategies, get_recent_learnings

MEMORY = Path("memory")
OUTPUTS = Path("outputs")
ROADMAP_FILE = MEMORY / "roadmap.json"

PROJECTS = {
    "yallaplays": {
        "domain": "yallaplays.com",
        "description": "Arabic gaming platform — top game discovery in Arab world",
        "market": "Arab world, 400M+ Arabic speakers",
        "monetization": "Ads, affiliate game links, premium features",
        "existing_pages": ["index.html", "category/action.html", "ar/index.html", "components/related-games.html"],
        "competitors": ["Y8.com (Arabic)", "Miniclip", "CrazyGames"],
        "key_metrics": {"monthly_visits": 145000, "bounce_rate": 40.5, "avg_session_m": 4.2},
    },
    "fionera": {
        "domain": "fionera.app",
        "description": "Turkish AI-powered finance dashboard — BIST stocks, crypto, portfolio",
        "market": "Turkey, 84M population, growing fintech market",
        "monetization": "Premium subscriptions, data feeds, affiliate broker links",
        "existing_pages": ["index.html", "widgets/bist-overview.html", "widgets/ai-insight.html", "widgets/portfolio-heatmap.html"],
        "competitors": ["Matriks", "Foreks", "IsYatirim"],
        "key_metrics": {"monthly_visits": 48230, "bounce_rate": 36.7, "avg_session_m": 6.1},
    },
    "mifteh": {
        "domain": "miftehos.com",
        "description": "MIFTEH AI Systems — autonomous AI software company",
        "market": "Global B2B, AI/SaaS buyers",
        "monetization": "B2B AI services, consulting, SaaS platform",
        "existing_pages": ["index.html", "services.html", "components/lead-funnel.html"],
        "competitors": ["Zapier AI", "Make.com", "Relevance AI"],
        "key_metrics": {"monthly_visits": 4500, "bounce_rate": 52.3, "avg_session_m": 2.8},
    },
}

SYSTEM_PROMPT = """You are a senior product strategist and growth consultant.
Analyze a project's current state and generate a prioritized product roadmap.
Focus on features that drive measurable outcomes: traffic, engagement, conversions, revenue.
Be specific, data-driven, and actionable. Return valid JSON only."""


def build_project_roadmap_prompt(project_key: str, config: dict, analytics: dict, memory_context: str, learnings: str) -> str:
    return f"""Analyze {project_key} ({config['domain']}) and generate a product roadmap.

PROJECT STATE:
{json.dumps({
    "description": config['description'],
    "market": config['market'],
    "monetization": config['monetization'],
    "existing_pages": config['existing_pages'],
    "key_metrics": config['key_metrics'],
}, indent=2)}

ANALYTICS INTELLIGENCE:
{json.dumps(analytics, indent=2)[:2000]}

MEMORY / WHAT WORKED:
{memory_context}

RECENT LEARNINGS:
{learnings}

COMPETITORS: {', '.join(config.get('competitors', []))}

Generate a roadmap JSON:
{{
  "project": "{project_key}",
  "seo_gaps": [
    {{
      "keyword": "<target keyword>",
      "est_monthly_volume": <integer>,
      "current_coverage": "none|partial|covered",
      "priority": "high|medium|low",
      "recommended_page": "<path/page.html>",
      "content_brief": "<2-sentence content brief>"
    }}
  ],
  "feature_gaps": [
    {{
      "feature": "<feature name>",
      "type": "page|widget|component|category_page|seo_hub",
      "problem_solved": "<user problem this solves>",
      "priority": "critical|high|medium|low",
      "effort": "low|medium|high",
      "estimated_impact": "<measurable outcome>",
      "recommended_path": "<file path>",
      "action_type": "generate_page|generate_widget|generate_feature|build_seo_cluster"
    }}
  ],
  "ux_gaps": [
    {{
      "issue": "<UX problem>",
      "page": "<affected page>",
      "fix": "<recommended fix>",
      "impact": "high|medium|low"
    }}
  ],
  "monetization_opportunities": [
    {{
      "opportunity": "<opportunity>",
      "type": "ads|affiliate|subscription|lead_gen|content",
      "est_monthly_revenue_usd": <integer>,
      "effort": "low|medium|high",
      "implementation": "<how to implement>"
    }}
  ],
  "engagement_opportunities": [
    {{
      "opportunity": "<engagement feature>",
      "target_metric": "<which metric improves>",
      "est_improvement_pct": <integer>,
      "implementation": "<brief implementation>"
    }}
  ],
  "priority_queue": [
    {{
      "rank": <1-10>,
      "item": "<feature/page name>",
      "type": "<type>",
      "action_type": "<action for executor>",
      "priority": "critical|high|medium",
      "estimated_traffic_impact": <monthly visits>,
      "estimated_revenue_impact_usd": <monthly USD>,
      "effort_days": <integer>,
      "roi_score": <0-100>,
      "project": "{project_key}",
      "recommendation": "<what to build>",
      "action": "<specific action description>"
    }}
  ],
  "summary": "<2-sentence roadmap summary>",
  "quick_wins": ["<item that can be done immediately>"],
  "90_day_goal": "<measurable goal for next 90 days>"
}}

Provide 5-8 SEO gaps, 5-8 feature gaps, 3-5 UX gaps, 3-5 monetization opps, 3-5 engagement opps, top 10 priority queue."""


def build_cross_project_roadmap_prompt(project_roadmaps: dict, learnings: str) -> str:
    # Summarize each project's priority queue
    summaries = {}
    for proj, rm in project_roadmaps.items():
        summaries[proj] = {
            "top_5": rm.get("priority_queue", [])[:5],
            "summary": rm.get("summary", ""),
            "quick_wins": rm.get("quick_wins", [])[:3],
        }

    return f"""Analyze the roadmaps for all 3 MIFTEH OS projects and generate a cross-project strategy.

PROJECT ROADMAPS:
{json.dumps(summaries, indent=2)[:3000]}

RECENT LEARNINGS:
{learnings}

Return JSON:
{{
  "portfolio_summary": "<2-sentence overall portfolio assessment>",
  "cross_project_patterns": ["<pattern observed across projects>"],
  "shared_opportunities": ["<opportunities applicable to all projects>"],
  "resource_allocation": {{
    "yallaplays": "<% of effort>",
    "fionera": "<% of effort>",
    "mifteh": "<% of effort>",
    "rationale": "<why this allocation>"
  }},
  "consolidated_priority_queue": [
    {{
      "rank": <integer>,
      "project": "<project>",
      "item": "<item>",
      "action_type": "<action>",
      "priority": "critical|high|medium",
      "estimated_traffic_impact": <integer>,
      "roi_score": <0-100>,
      "recommendation": "<what to build>",
      "action": "<specific action>"
    }}
  ],
  "system_improvements": ["<improvement to MIFTEH OS itself>"],
  "next_sprint_plan": ["<concrete action for next 7 days>"]
}}"""


def load_analytics_intel(project_key: str) -> dict:
    """Load per-project analytics from analytics_intelligence.json."""
    f = MEMORY / "analytics_intelligence.json"
    if not f.exists():
        return {}
    try:
        intel = json.loads(f.read_text())
        return intel.get("projects", {}).get(project_key, {})
    except Exception:
        return {}


def generate_project_roadmap(project_key: str) -> dict | None:
    config = PROJECTS[project_key]
    analytics = load_analytics_intel(project_key)
    mem_context = get_memory_context(project_key, "page")
    learnings = get_recent_learnings(1)
    learnings_str = learnings[0].get("key_insight", "") if learnings else ""

    print(f"  [roadmap] Generating {project_key} roadmap...")
    sys_prompt = SYSTEM_PROMPT
    user_prompt = build_project_roadmap_prompt(project_key, config, analytics, mem_context, learnings_str)

    data, tokens, cost, ok = generate_json(sys_prompt, user_prompt, max_tokens=3000)
    if not ok or not data:
        print(f"  [roadmap] {project_key}: AI call failed")
        return None

    data["generated_at"] = now_iso()
    data["tokens_used"] = tokens
    data["cost_usd"] = cost
    print(f"  [roadmap] {project_key}: {len(data.get('priority_queue',[]))} items in queue — {tokens} tokens")
    return data


def main():
    print("[roadmap] Starting product roadmap engine...")
    force = os.environ.get("FORCE_REGENERATE", "").lower() in ("1", "true", "yes")
    target_project = os.environ.get("TARGET_PROJECT", "all").lower()

    existing = {}
    if ROADMAP_FILE.exists() and not force:
        try:
            existing = json.loads(ROADMAP_FILE.read_text())
        except Exception:
            pass

    project_roadmaps = existing.get("projects", {})
    total_tokens, total_cost = 0, 0.0

    for project_key in PROJECTS:
        if target_project != "all" and project_key != target_project:
            continue
        if not force and project_key in project_roadmaps:
            print(f"  [roadmap] {project_key}: using cached roadmap (use FORCE_REGENERATE=1 to refresh)")
            continue
        rm = generate_project_roadmap(project_key)
        if rm:
            project_roadmaps[project_key] = rm
            total_tokens += rm.get("tokens_used", 0)
            total_cost += rm.get("cost_usd", 0.0)

    # Cross-project synthesis
    learnings = get_recent_learnings(1)
    learnings_str = learnings[0].get("key_insight", "") if learnings else ""

    cross_project = {}
    if len(project_roadmaps) >= 2:
        print("  [roadmap] Generating cross-project strategy...")
        user_prompt = build_cross_project_roadmap_prompt(project_roadmaps, learnings_str)
        cross_data, tokens, cost, ok = generate_json(SYSTEM_PROMPT, user_prompt, max_tokens=2000)
        if ok and cross_data:
            cross_project = cross_data
            total_tokens += tokens
            total_cost += cost
            print(f"  [roadmap] Cross-project: {len(cross_data.get('consolidated_priority_queue', []))} items")

    # Consolidate all priority queue items for decision engine
    all_decisions = []
    for proj, rm in project_roadmaps.items():
        for item in rm.get("priority_queue", []):
            all_decisions.append({**item, "project": proj})

    # Also add cross-project consolidated queue
    for item in cross_project.get("consolidated_priority_queue", []):
        if item not in all_decisions:
            all_decisions.append(item)

    # Sort by ROI score
    all_decisions.sort(key=lambda x: x.get("roi_score", 0), reverse=True)

    roadmap = {
        "generated_at": now_iso(),
        "total_tokens_used": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "projects": project_roadmaps,
        "cross_project": cross_project,
        "consolidated_priority_queue": all_decisions[:30],
        "total_items": len(all_decisions),
    }

    ROADMAP_FILE.write_text(json.dumps(roadmap, indent=2, ensure_ascii=False))
    print(f"\n[roadmap] Saved → {ROADMAP_FILE}")
    print(f"[roadmap] {len(all_decisions)} items | {total_tokens} tokens | ${total_cost:.5f}")

    # Inject top decisions into analytics_intelligence.json for autonomous executor
    intel_file = MEMORY / "analytics_intelligence.json"
    if intel_file.exists():
        try:
            intel = json.loads(intel_file.read_text())
            intel["autonomous_decisions"] = all_decisions[:20]
            intel["generated_at"] = now_iso()
            intel_file.write_text(json.dumps(intel, indent=2, ensure_ascii=False))
            print(f"[roadmap] Injected {min(20, len(all_decisions))} decisions into executor queue")
        except Exception as e:
            print(f"[roadmap] Could not update intelligence file: {e}")

    return roadmap


if __name__ == "__main__":
    main()
