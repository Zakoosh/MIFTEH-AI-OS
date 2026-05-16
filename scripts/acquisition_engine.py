"""
MIFTEH OS — Acquisition Engine
Viral content generation, SEO cluster expansion, social campaign generation,
launch sequencing, outreach opportunities, growth loops.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

PROJECTS = {
    "yallaplays": {
        "niche": "Arabic gaming",
        "audience": "Arabic-speaking gamers aged 13-35",
        "channels": ["twitter", "tiktok", "youtube", "instagram", "discord"],
        "viral_formats": ["gameplay_clips", "gaming_memes", "challenge_videos", "game_reviews", "top10_lists"],
        "growth_loops": ["share_score", "invite_friends", "weekly_tournament", "daily_challenge"],
        "seo_language": "ar",
    },
    "fionera": {
        "niche": "Turkish finance",
        "audience": "Turkish retail investors aged 25-55",
        "channels": ["twitter", "instagram", "linkedin", "youtube", "telegram"],
        "viral_formats": ["market_alerts", "portfolio_performance", "investment_tips", "market_analysis", "news_reactions"],
        "growth_loops": ["share_portfolio", "refer_friend", "watchlist_share", "daily_market_email"],
        "seo_language": "tr",
    },
    "mifteh": {
        "niche": "AI business automation",
        "audience": "Business owners and operators aged 30-55",
        "channels": ["linkedin", "twitter", "youtube", "email", "reddit"],
        "viral_formats": ["case_studies", "roi_calculators", "how_to_guides", "tool_comparisons", "automation_demos"],
        "growth_loops": ["free_audit_referral", "case_study_feature", "partner_program", "content_collaboration"],
        "seo_language": "en",
    },
}

OUTREACH_TYPES = [
    "influencer_partnership", "press_coverage", "podcast_appearance",
    "community_sponsorship", "cross_promotion", "affiliate_program",
]

LAUNCH_PHASES = [
    "soft_launch", "community_seeding", "content_burst",
    "paid_amplification", "viral_loop_activation",
]

SEO_CLUSTER_TEMPLATE = {
    "pillar_page": 1,
    "hub_pages": 3,
    "spoke_articles": 10,
    "faq_pages": 8,
}


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def load_sources():
    return {
        "growth": _rj("growth_report.json"),
        "social": _rj("social_signals.json"),
        "campaigns": _rj("campaign_report.json"),
        "seo": _rj("seo_opportunities.json"),
        "analytics": _rj("analytics_intelligence.json"),
    }


def generate_viral_content_plan(project_id, config, sources):
    social = sources["social"].get("projects", {}).get(project_id, {})
    trending_keywords = social.get("trending_keywords", [])

    content_ideas = []
    for i, fmt in enumerate(config["viral_formats"][:4]):
        kw_hint = trending_keywords[i % len(trending_keywords)] if trending_keywords else fmt.replace("_", " ")
        reach_base = [50000, 20000, 10000, 5000][i]
        content_ideas.append({
            "format": fmt,
            "hook": f"Trending: {kw_hint}",
            "estimated_reach": reach_base,
            "virality_score": round(0.9 - i * 0.12, 2),
            "primary_platform": config["channels"][i % len(config["channels"])],
            "production_effort": ["low", "medium", "medium", "high"][i % 4],
            "repurpose_to": config["channels"][:2],
        })

    return sorted(content_ideas, key=lambda x: x["virality_score"], reverse=True)


def build_seo_cluster_expansion(project_id, config, sources):
    seo_data = sources["seo"].get("projects", {}).get(project_id, {})
    existing_clusters = len(seo_data.get("topical_clusters", []))

    growth_data = sources["growth"].get("projects", {}).get(project_id, {})
    authority_plan = growth_data.get("topical_authority_plan", [])

    cluster_plan = []
    for pillar_data in authority_plan[:3]:
        pillar = pillar_data.get("pillar", "content")
        total_pages = sum(SEO_CLUSTER_TEMPLATE.values())
        cluster_plan.append({
            "pillar": pillar,
            "content_breakdown": SEO_CLUSTER_TEMPLATE,
            "total_pages": total_pages,
            "language": config["seo_language"],
            "estimated_traffic_gain": pillar_data.get("estimated_traffic_gain", 500),
            "timeline_weeks": 8,
            "priority": "high" if pillar_data.get("estimated_traffic_gain", 0) > 800 else "medium",
        })

    return {
        "current_clusters": existing_clusters,
        "target_clusters": existing_clusters + len(cluster_plan) * 3,
        "new_pages_planned": sum(c["total_pages"] for c in cluster_plan),
        "cluster_plan": cluster_plan,
    }


def generate_social_campaign(project_id, config):
    return {
        "campaign_name": f"{project_id.title()} Growth Sprint — 30 Days",
        "duration_days": 30,
        "channels": config["channels"],
        "posting_cadence": {
            "daily_short_form": 2,
            "weekly_long_form": 1,
            "monthly_hero_piece": 1,
        },
        "content_mix": {
            "educational": 0.40,
            "entertaining": 0.30,
            "promotional": 0.20,
            "community": 0.10,
        },
        "hashtag_strategy": {
            "branded": [f"#{project_id}"],
            "niche": [f"#{config['niche'].replace(' ', '').lower()}"],
            "reach": ["#trending", "#viral", "#ai"],
        },
        "kpi_targets": {
            "follower_growth": 1000,
            "avg_reach_per_post": 5000,
            "engagement_rate_pct": 3.5,
            "profile_visits_per_week": 500,
        },
        "best_post_times": {
            config["channels"][0]: "18:00-20:00 local",
            config["channels"][1]: "12:00-14:00 local",
        },
    }


def generate_growth_loops(project_id, config):
    loops = []
    for i, loop in enumerate(config["growth_loops"]):
        loops.append({
            "loop_name": loop,
            "mechanism": f"User completes action → triggers {loop} → new user acquired",
            "viral_coefficient": round(0.25 + i * 0.08, 2),
            "avg_new_users_per_activation": round(0.5 + i * 0.3, 1),
            "implementation_complexity": ["low", "medium", "high", "medium"][i % 4],
            "cac_reduction_pct": (i + 1) * 8,
            "requires_feature": loop.replace("_", " ").title(),
        })
    return loops


def generate_outreach_plan(project_id, config):
    plan = []
    targets_by_type = [8, 3, 5, 10, 3, 0]
    reach_by_type = [80000, 500000, 30000, 50000, 40000, 0]
    priority_by_type = ["high", "medium", "high", "low", "medium", "low"]

    for i, otype in enumerate(OUTREACH_TYPES[:4]):
        plan.append({
            "type": otype,
            "niche": config["niche"],
            "target_count": targets_by_type[i],
            "estimated_total_reach": reach_by_type[i],
            "timeline_weeks": [4, 8, 6, 2][i % 4],
            "priority": priority_by_type[i],
            "expected_backlinks": [targets_by_type[i] * 1, 0, targets_by_type[i] * 2, targets_by_type[i]][i % 4],
        })
    return sorted(plan, key=lambda x: {"high": 3, "medium": 2, "low": 1}.get(x["priority"], 0), reverse=True)


def generate_launch_sequence(project_id, config, sources):
    sequence = []
    budgets = [0, 50, 200, 500, 0]
    success_metrics = ["50 engaged users", "500 engagements", "1000 visitors", "50 signups", "K-factor > 1.0"]

    for i, phase in enumerate(LAUNCH_PHASES):
        sequence.append({
            "phase": phase,
            "week": i + 1,
            "focus": ["Build audience", "Seed community", "Drive traffic", "Convert users", "Activate virality"][i],
            "actions": [
                f"Execute {phase.replace('_', ' ')} strategy for {project_id}",
                f"Measure {['reach', 'engagement', 'traffic', 'conversions', 'virality'][i]}",
            ],
            "success_metric": success_metrics[i],
            "budget_usd": budgets[i],
        })
    return sequence


def ai_acquisition_strategy(project_id, config, viral, cluster, loops, sources):
    system = (
        "You are a growth hacker and user acquisition expert. "
        "Generate specific, executable acquisition strategies. Return valid JSON only."
    )
    analytics = sources["analytics"].get("projects", {}).get(project_id, {})
    current_sessions = analytics.get("overview", {}).get("monthly_sessions", 0)

    prompt = f"""Project: {project_id}
Niche: {config['niche']}
Target audience: {config['audience']}
Primary channels: {config['channels'][:3]}
Current monthly sessions: {current_sessions}
Top viral format: {viral[0]['format'] if viral else 'content'}
SEO cluster target: +{cluster.get('new_pages_planned', 22)} pages
Growth loops: {[l['loop_name'] for l in loops]}

Generate user acquisition strategy. Return JSON:
{{
  "acquisition_summary": "2-sentence opportunity overview",
  "primary_acquisition_channel": "highest ROI channel",
  "cac_estimate_usd": 0.0,
  "ltv_estimate_usd": 0.0,
  "ltv_cac_ratio": 0.0,
  "month_1_session_target": 0,
  "month_3_session_target": 0,
  "viral_coefficient_target": 0.0,
  "top_growth_levers": ["lever1", "lever2", "lever3"],
  "budget_allocation": {{
    "content_creation": 0.0,
    "paid_social": 0.0,
    "outreach": 0.0,
    "tools": 0.0
  }},
  "week_1_actions": ["action1", "action2", "action3"],
  "90_day_traffic_target": 0
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 600)
    if not ok:
        data = {
            "acquisition_summary": f"Multi-channel acquisition for {config['niche']} via SEO + social + referral.",
            "primary_acquisition_channel": config["channels"][0],
            "cac_estimate_usd": 5.0,
            "ltv_estimate_usd": 35.0,
            "ltv_cac_ratio": 7.0,
            "month_1_session_target": max(current_sessions, 1000) + 500,
            "month_3_session_target": max(current_sessions, 1000) * 3,
            "viral_coefficient_target": 0.4,
            "top_growth_levers": ["SEO content cluster", "Social viral loop", "Referral program"],
            "budget_allocation": {"content_creation": 0.50, "paid_social": 0.20, "outreach": 0.20, "tools": 0.10},
            "week_1_actions": ["Publish 3 viral content pieces", "Launch referral program", "Outreach to 5 creators"],
            "90_day_traffic_target": max(current_sessions, 1000) * 5,
        }
    return data, tokens, cost


def main():
    print("[acquisition_engine] Starting acquisition analysis...")
    sources = load_sources()

    all_tokens, all_cost = 0, 0.0
    project_reports = {}
    total_m1 = 0
    total_m3 = 0

    for project_id, config in PROJECTS.items():
        print(f"[acquisition_engine] Analyzing {project_id}...")

        viral = generate_viral_content_plan(project_id, config, sources)
        cluster = build_seo_cluster_expansion(project_id, config, sources)
        campaign = generate_social_campaign(project_id, config)
        loops = generate_growth_loops(project_id, config)
        outreach = generate_outreach_plan(project_id, config)
        launch = generate_launch_sequence(project_id, config, sources)

        strategy, tokens, cost = ai_acquisition_strategy(project_id, config, viral, cluster, loops, sources)
        all_tokens += tokens
        all_cost += cost

        project_reports[project_id] = {
            "viral_content_plan": viral,
            "seo_cluster_expansion": cluster,
            "social_campaign": campaign,
            "growth_loops": loops,
            "outreach_plan": outreach,
            "launch_sequence": launch,
            "ai_strategy": strategy,
        }

        total_m1 += strategy.get("month_1_session_target", 0)
        total_m3 += strategy.get("month_3_session_target", 0)

    report = {
        "generated_at": now_iso(),
        "portfolio_month_1_session_target": total_m1,
        "portfolio_month_3_session_target": total_m3,
        "projects": project_reports,
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "acquisition_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[acquisition_engine] Done — M1 target {total_m1} sessions, M3 target {total_m3}, ${all_cost:.4f}")


if __name__ == "__main__":
    main()
