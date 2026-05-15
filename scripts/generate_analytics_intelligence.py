"""
MIFTEH OS — Analytics Intelligence Engine
Generates AI-estimated behavioral analytics for all 3 projects, then runs a
decision-engine pass to produce recommendations and an autonomous work queue.

Data source: "ai_intelligence" (model-estimated from site context + industry benchmarks).
Designed so real analytics (Plausible / GA4 export) can replace AI-generated
values in future by swapping the ingestion phase while keeping the analysis flow.

Focus modes (FOCUS env var):
  analytics   — generate full analytics data (default)
  engagement  — focus on session-depth and engagement scoring
  traffic     — focus on SEO + traffic opportunities
  conversion  — focus on funnel + CTA optimization

Writes:
  memory/analytics_intelligence.json   — full intelligence report
  outputs/{project}/analytics/*.json   — per-project records
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, today_str, timestamp_str

MEMORY_DIR = Path("memory")
OUTPUT_DIR = Path("outputs")
FOCUS = os.environ.get("FOCUS", "analytics").lower()

# ─── Per-project context ──────────────────────────────────────────────────────

PROJECTS = {
    "yallaplays": {
        "domain": "yallaplays.com",
        "description": "Arabic browser gaming platform, mid-size, ~2 years old, dark gaming theme, mobile-first, Arab-world audience",
        "tech": "Static HTML, RTL Arabic, gaming categories",
        "market": "Arabic gaming, primary markets: Saudi Arabia, Egypt, UAE, Iraq",
        "existing_pages": ["index.html", "category/action.html", "ar/index.html", "components/related-games.html"],
        "monetization": "display ads, sponsored games",
        "industry_benchmarks": {"monthly_visits_range": "80000-200000", "mobile_pct": "65-80", "bounce_pct": "35-52"},
    },
    "fionera": {
        "domain": "fionera.app",
        "description": "Turkish AI-powered finance dashboard, BIST stocks, crypto, portfolio tracking, niche product",
        "tech": "SPA, dark finance theme, Turkish language",
        "market": "Turkish retail investors and finance enthusiasts",
        "existing_pages": ["index.html", "widgets/bist-overview.html", "widgets/ai-insight.html", "widgets/portfolio-heatmap.html"],
        "monetization": "premium subscription, data provider partnerships",
        "industry_benchmarks": {"monthly_visits_range": "25000-75000", "mobile_pct": "38-55", "bounce_pct": "30-45"},
    },
    "mifteh": {
        "domain": "miftehos.com",
        "description": "MIFTEH AI Systems — autonomous AI software company, B2B, relatively new site",
        "tech": "Static HTML, dark tech theme, English, AI agency",
        "market": "Startups and businesses wanting AI automation",
        "existing_pages": ["index.html", "services.html", "components/lead-funnel.html"],
        "monetization": "B2B service contracts, AI automation retainers",
        "industry_benchmarks": {"monthly_visits_range": "2000-10000", "mobile_pct": "30-50", "bounce_pct": "45-65"},
    },
}

# ─── Prompt builders ──────────────────────────────────────────────────────────

ANALYTICS_SYSTEM = """You are a senior web analytics expert. Generate realistic, internally-consistent analytics data.
Return ONLY valid JSON — no markdown, no explanation. All numbers must be realistic for the site type described.
Use industry benchmarks provided. Make the data tell a coherent story about a real site's performance."""


def build_analytics_prompt(project_key, config):
    focus_extra = {
        "engagement": "Focus especially on scroll depth, session duration, click rates, and return visitor metrics.",
        "traffic": "Focus especially on organic search data, keyword rankings, and traffic acquisition.",
        "conversion": "Focus especially on funnel steps, CTA click rates, and goal completions.",
        "analytics": "",
    }.get(FOCUS, "")

    existing = ", ".join(config["existing_pages"])
    return f"""Generate realistic 30-day analytics data for {config['domain']}.

SITE: {config['description']}
MARKET: {config['market']}
EXISTING PAGES: {existing}
MONETIZATION: {config['monetization']}
BENCHMARKS: {json.dumps(config['industry_benchmarks'])}
{focus_extra}

Return exactly this JSON structure with realistic values:
{{
  "overview": {{
    "monthly_visits": <int within benchmark range>,
    "daily_avg": <monthly_visits / 30>,
    "weekly_change_pct": <float -15.0 to +28.0, reflects realistic trends>,
    "bounce_rate_pct": <float within benchmark range>,
    "avg_session_seconds": <int 150-480>,
    "pages_per_session": <float 2.0-6.0>,
    "mobile_pct": <float within benchmark range>,
    "new_users_pct": <float 35.0-60.0>,
    "organic_search_pct": <float 35.0-70.0>,
    "direct_pct": <float 15.0-35.0>,
    "referral_pct": <float 5.0-20.0>
  }},
  "top_pages": [
    {{"path": "<actual page path>", "monthly_visits": <int>, "bounce_pct": <float>, "avg_time_seconds": <int>, "trend": "<up|down|stable>", "ctr_pct": <float 2.0-12.0>}}
  ],
  "low_pages": [
    {{"path": "<actual page path>", "monthly_visits": <int low>, "bounce_pct": <float high>, "avg_time_seconds": <int low>, "issue": "<specific actionable issue description>", "fix_priority": "<high|medium|low>"}}
  ],
  "top_content": [
    {{"label": "<content type or category name>", "visits": <int>, "growth_pct": <float>, "engagement_score": <int 0-100>}}
  ],
  "search_queries": [
    {{"query": "<realistic query in correct language>", "clicks": <int>, "impressions": <int>, "ctr_pct": <float 1.0-15.0>, "avg_position": <float 1.0-50.0>, "opportunity": "<high|medium|low>"}}
  ],
  "engagement": {{
    "avg_scroll_depth_pct": <float 40.0-75.0>,
    "primary_cta_ctr_pct": <float 1.5-8.0>,
    "internal_link_ctr_pct": <float 4.0-18.0>,
    "return_visitor_pct": <float 25.0-55.0>,
    "engagement_events_per_session": <float 2.0-8.0>
  }},
  "conversions": {{
    "primary_goal_rate_pct": <float 0.5-8.0>,
    "micro_conversion_rate_pct": <float 2.0-15.0>,
    "funnel_drop_off_pct": <float 30.0-75.0>,
    "best_converting_page": "<page path>",
    "worst_converting_page": "<page path>"
  }},
  "scores": {{
    "performance_score": <int 45-85>,
    "engagement_score": <int 45-85>,
    "seo_opportunity_score": <int 55-95>,
    "conversion_score": <int 30-80>,
    "overall_health": <int 45-85>
  }},
  "top_opportunity": "<1-2 sentence specific, actionable growth opportunity for this site>"
}}

Include at least 5 top_pages, 3 low_pages, 5 top_content items, 6 search_queries.
Make all paths match the EXISTING PAGES where applicable. Add realistic missing-but-expected pages too."""


ANALYSIS_SYSTEM = """You are a senior growth analyst and AI product strategist. Analyze multi-project analytics data.
Return ONLY valid JSON. Be specific and actionable. Prioritize by business impact."""


def build_analysis_prompt(all_analytics):
    summaries = {}
    for proj, data in all_analytics.items():
        ov = data.get("overview", {})
        sc = data.get("scores", {})
        summaries[proj] = {
            "monthly_visits": ov.get("monthly_visits", 0),
            "bounce_rate_pct": ov.get("bounce_rate_pct", 0),
            "avg_session_seconds": ov.get("avg_session_seconds", 0),
            "weekly_change_pct": ov.get("weekly_change_pct", 0),
            "scores": sc,
            "top_opportunity": data.get("top_opportunity", ""),
            "low_pages_count": len(data.get("low_pages", [])),
            "top_search_query": (data.get("search_queries") or [{}])[0].get("query", ""),
        }

    return f"""Analyze this multi-project analytics intelligence report and generate recommendations + decisions.

ANALYTICS SUMMARY:
{json.dumps(summaries, indent=2)}

Return exactly this JSON:
{{
  "cross_project": {{
    "total_monthly_visits": <sum of all monthly_visits>,
    "strongest_project": "<project key with best overall_health>",
    "highest_seo_opportunity": "<project key with highest seo_opportunity_score>",
    "most_critical_issues": "<project key with most low_pages or worst score>",
    "overall_portfolio_health": <int avg of all overall_health scores>,
    "month_over_month_trend": "<up|down|stable>",
    "insight": "<2-3 sentence cross-portfolio insight>"
  }},
  "recommendations": [
    {{
      "id": "rec_001",
      "project": "<yallaplays|fionera|mifteh>",
      "type": "<seo_page|widget|content|cta_improvement|metadata|internal_links|new_feature>",
      "priority": "<critical|high|medium|low>",
      "title": "<concise action title>",
      "description": "<2-3 sentence specific description of what to build and why>",
      "rationale": "<specific metric from analytics that justifies this>",
      "est_traffic_impact": <int monthly visits gain>,
      "est_conversion_impact_pct": <float improvement percentage>,
      "effort": "<low|medium|high>",
      "action_type": "<generate_page|generate_widget|improve_metadata|generate_content>",
      "target_path": "<suggested file path in target repo>"
    }}
  ],
  "alert_thresholds": [
    {{
      "project": "<project>",
      "metric": "<metric name>",
      "current_value": <number>,
      "threshold": <number>,
      "severity": "<critical|warning|info>",
      "message": "<alert message>"
    }}
  ]
}}

Generate exactly 8 recommendations (mix of projects and types, ordered by priority).
Generate 4-6 alert thresholds (things that need attention).
Be very specific — reference actual page paths and metrics."""


DECISIONS_SYSTEM = """You are the autonomous AI OS decision engine for MIFTEH. You create a prioritized work queue.
Return ONLY valid JSON. Be specific about WHAT to generate and WHERE."""


def build_decisions_prompt(recommendations, all_analytics):
    # Pass top 5 recs
    top_recs = (recommendations or [])[:5]
    visit_data = {k: v.get("overview", {}).get("monthly_visits", 0) for k, v in all_analytics.items()}

    return f"""Based on these analytics recommendations, create an autonomous execution queue.

TOP RECOMMENDATIONS:
{json.dumps(top_recs, indent=2)}

CURRENT TRAFFIC:
{json.dumps(visit_data)}

Return exactly this JSON:
{{
  "queue": [
    {{
      "id": "dec_001",
      "project": "<project key>",
      "priority": <int 1-10, 1=highest>,
      "type": "<page_generation|widget_generation|metadata_optimization|seo_cluster|content>",
      "title": "<what the AI will autonomously build>",
      "rationale": "<why this is the #1 priority based on data>",
      "target_file": "<exact file path in target repo>",
      "target_repo": "<owner/repo>",
      "feature_type": "<category_page|seo_hub|widget|component|page>",
      "estimated_impact": {{
        "monthly_visits": <int>,
        "engagement_improvement_pct": <float>,
        "conversion_improvement_pct": <float>
      }},
      "auto_mergeable": <true if new file, false if modifying critical existing>,
      "status": "queued"
    }}
  ],
  "execution_summary": "<2-3 sentence description of the autonomous strategy>",
  "estimated_total_impact": {{
    "monthly_visits_gain": <int total across all decisions>,
    "new_pages": <int>,
    "new_widgets": <int>
  }}
}}

Generate exactly 6 queued decisions ordered by priority (1=most important)."""

# ─── Storage ──────────────────────────────────────────────────────────────────

def save_project_analytics(project_key, analytics_data, tokens, cost):
    ts = timestamp_str()
    out_dir = OUTPUT_DIR / project_key / "analytics"
    out_dir.mkdir(parents=True, exist_ok=True)
    record = {
        "project": project_key,
        "operation_type": "analytics_intelligence",
        "focus": FOCUS,
        "data_source": "ai_intelligence",
        "period": "last_30_days",
        "generated_at": now_iso(),
        "ai_generated": True,
        "ai_provider": "openai",
        "tokens_used": tokens,
        "cost_usd": cost,
        "title": f"Analytics Intelligence — {project_key}",
        **analytics_data,
    }
    (out_dir / f"{ts}_analytics.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
    return record


def save_intelligence_report(report):
    MEMORY_DIR.mkdir(exist_ok=True)
    (MEMORY_DIR / "analytics_intelligence.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False)
    )


# ─── Main pipeline ────────────────────────────────────────────────────────────

def main():
    print(f"[analytics] Starting intelligence cycle — focus={FOCUS} — {now_iso()}")

    total_tokens, total_cost = 0, 0.0
    all_analytics = {}

    # Phase 1: Generate analytics per project
    for project_key, config in PROJECTS.items():
        print(f"\n[analytics] {project_key.upper()} — generating analytics...")
        prompt = build_analytics_prompt(project_key, config)
        data, tokens, cost, ok = generate_json(ANALYTICS_SYSTEM, prompt, max_tokens=2200)
        total_tokens += tokens
        total_cost += cost

        if not ok or not data:
            print(f"  [!] Generation failed for {project_key}")
            # Fallback minimal data
            data = {
                "overview": {"monthly_visits": 50000, "bounce_rate_pct": 45.0,
                             "avg_session_seconds": 240, "mobile_pct": 60.0,
                             "weekly_change_pct": 0.0, "organic_search_pct": 50.0,
                             "daily_avg": 1667, "pages_per_session": 3.0,
                             "new_users_pct": 45.0},
                "top_pages": [], "low_pages": [], "top_content": [],
                "search_queries": [], "engagement": {}, "conversions": {},
                "scores": {"performance_score": 65, "engagement_score": 65,
                           "seo_opportunity_score": 70, "conversion_score": 55, "overall_health": 65},
                "top_opportunity": "Improve content depth and SEO coverage.",
            }
        else:
            record = save_project_analytics(project_key, data, tokens, cost)
            ov = data.get("overview", {})
            sc = data.get("scores", {})
            print(f"  Visits: {ov.get('monthly_visits',0):,}/mo  Bounce: {ov.get('bounce_rate_pct',0):.1f}%  "
                  f"Health: {sc.get('overall_health',0)}  SEO opp: {sc.get('seo_opportunity_score',0)}")
            print(f"  Opportunity: {data.get('top_opportunity','')[:80]}")

        all_analytics[project_key] = data

    # Phase 2: Cross-project analysis + recommendations
    print(f"\n[analytics] Running cross-project analysis + recommendations...")
    analysis_prompt = build_analysis_prompt(all_analytics)
    analysis_data, tokens, cost, ok = generate_json(ANALYSIS_SYSTEM, analysis_prompt, max_tokens=2500)
    total_tokens += tokens
    total_cost += cost

    if not ok or not analysis_data:
        print(f"  [!] Analysis failed — using defaults")
        analysis_data = {
            "cross_project": {"total_monthly_visits": sum(
                v.get("overview", {}).get("monthly_visits", 0) for v in all_analytics.values()
            ), "insight": "Analytics cycle complete."},
            "recommendations": [],
            "alert_thresholds": [],
        }
    else:
        cp = analysis_data.get("cross_project", {})
        recs = analysis_data.get("recommendations", [])
        alerts = analysis_data.get("alert_thresholds", [])
        print(f"  Total visits: {cp.get('total_monthly_visits',0):,}")
        print(f"  Strongest: {cp.get('strongest_project','?')} | Highest SEO opp: {cp.get('highest_seo_opportunity','?')}")
        print(f"  Recommendations: {len(recs)} | Alerts: {len(alerts)}")
        print(f"  Insight: {cp.get('insight','')[:100]}")

    recommendations = analysis_data.get("recommendations", [])

    # Phase 3: Autonomous decision queue
    print(f"\n[analytics] Generating autonomous decision queue...")
    decisions_prompt = build_decisions_prompt(recommendations, all_analytics)
    decisions_data, tokens, cost, ok = generate_json(DECISIONS_SYSTEM, decisions_prompt, max_tokens=2000)
    total_tokens += tokens
    total_cost += cost

    if not ok or not decisions_data:
        print(f"  [!] Decision generation failed")
        decisions_data = {"queue": [], "execution_summary": "Decision engine unavailable.", "estimated_total_impact": {}}
    else:
        queue = decisions_data.get("queue", [])
        summary = decisions_data.get("execution_summary", "")
        impact = decisions_data.get("estimated_total_impact", {})
        print(f"  Queue: {len(queue)} decisions")
        print(f"  Est impact: +{impact.get('monthly_visits_gain',0):,} visits/mo, "
              f"{impact.get('new_pages',0)} pages, {impact.get('new_widgets',0)} widgets")
        print(f"  Strategy: {summary[:100]}")
        for i, dec in enumerate(queue[:3], 1):
            print(f"    #{i} [{dec.get('project','?')}] {dec.get('title','')}")

    # Assemble full report
    cross = analysis_data.get("cross_project", {})
    report = {
        "generated_at": now_iso(),
        "focus": FOCUS,
        "data_source": "ai_intelligence",
        "period": "last_30_days",
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),

        "cross_project": {
            "total_monthly_visits": cross.get("total_monthly_visits",
                sum(v.get("overview", {}).get("monthly_visits", 0) for v in all_analytics.values())),
            "strongest_project": cross.get("strongest_project", ""),
            "highest_seo_opportunity": cross.get("highest_seo_opportunity", ""),
            "most_critical_issues": cross.get("most_critical_issues", ""),
            "overall_portfolio_health": cross.get("overall_portfolio_health", 0),
            "month_over_month_trend": cross.get("month_over_month_trend", "stable"),
            "insight": cross.get("insight", ""),
        },

        "projects": {
            pk: {
                "overview": pd.get("overview", {}),
                "scores": pd.get("scores", {}),
                "top_pages": pd.get("top_pages", [])[:5],
                "low_pages": pd.get("low_pages", [])[:3],
                "top_content": pd.get("top_content", [])[:5],
                "search_queries": pd.get("search_queries", [])[:6],
                "engagement": pd.get("engagement", {}),
                "conversions": pd.get("conversions", {}),
                "top_opportunity": pd.get("top_opportunity", ""),
            }
            for pk, pd in all_analytics.items()
        },

        "recommendations": recommendations,
        "alert_thresholds": analysis_data.get("alert_thresholds", []),
        "autonomous_decisions": decisions_data.get("queue", []),
        "execution_summary": decisions_data.get("execution_summary", ""),
        "estimated_impact": decisions_data.get("estimated_total_impact", {}),
    }

    save_intelligence_report(report)

    # Print final summary
    total_visits = report["cross_project"]["total_monthly_visits"]
    queue_count = len(report["autonomous_decisions"])
    rec_count = len(report["recommendations"])

    print(f"\n{'='*60}")
    print(f"[analytics] CYCLE COMPLETE — {now_iso()}")
    print(f"  Total portfolio visits : {total_visits:,}/month")
    print(f"  Recommendations        : {rec_count}")
    print(f"  Autonomous decisions   : {queue_count}")
    print(f"  Total tokens           : {total_tokens:,}")
    print(f"  Total cost             : ${total_cost:.5f}")
    print(f"  Report saved           : memory/analytics_intelligence.json")


if __name__ == "__main__":
    main()
