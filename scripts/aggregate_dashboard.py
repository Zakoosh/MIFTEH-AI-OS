"""
MIFTEH OS — Dashboard Aggregator
Reads all output files, builds frontend/dashboard/data/dashboard.json.
This file is served at miftehos.com/data/dashboard.json — no backend required.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import now_iso

LOOPS = [
    # YallaPlays (6)
    {"id": "yp-seo-loop",      "label": "SEO Page Generator",       "project": "yallaplays", "interval_minutes": 360},
    {"id": "yp-category-loop", "label": "Category Optimizer",        "project": "yallaplays", "interval_minutes": 720},
    {"id": "yp-homepage-loop", "label": "Homepage Recommendations",  "project": "yallaplays", "interval_minutes": 360},
    {"id": "yp-linking-loop",  "label": "Internal Linking",          "project": "yallaplays", "interval_minutes": 1440},
    {"id": "yp-mobile-loop",   "label": "Mobile Optimization",       "project": "yallaplays", "interval_minutes": 1440},
    {"id": "yp-games-loop",    "label": "Game Suggestion Generator", "project": "yallaplays", "interval_minutes": 240},
    # Fionera (5)
    {"id": "fi-market-loop",   "label": "Market Insights",           "project": "fionera",    "interval_minutes": 240},
    {"id": "fi-watchlist-loop","label": "Watchlist Optimizer",       "project": "fionera",    "interval_minutes": 360},
    {"id": "fi-analytics-loop","label": "Analytics Report",          "project": "fionera",    "interval_minutes": 1440},
    {"id": "fi-ux-loop",       "label": "UX Improvements",           "project": "fionera",    "interval_minutes": 1440},
    {"id": "fi-widgets-loop",  "label": "Finance Widgets",           "project": "fionera",    "interval_minutes": 720},
    # Mifteh (3)
    {"id": "mi-seo-loop",      "label": "SEO Improvements",          "project": "mifteh",     "interval_minutes": 720},
    {"id": "mi-content-loop",  "label": "Content Optimizer",         "project": "mifteh",     "interval_minutes": 1440},
    {"id": "mi-landing-loop",  "label": "Landing Page Optimizer",    "project": "mifteh",     "interval_minutes": 1440},
]


def read_outputs():
    outputs = []
    for project_dir in Path("outputs").iterdir():
        if not project_dir.is_dir() or project_dir.name.startswith("."):
            continue
        for type_dir in project_dir.iterdir():
            if not type_dir.is_dir():
                continue
            for f in type_dir.glob("*.json"):
                if f.name == "latest.json":
                    continue
                try:
                    outputs.append(json.loads(f.read_text()))
                except Exception:
                    pass
    outputs.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
    return outputs


def read_prs():
    f = Path("memory/all_prs.json")
    return json.loads(f.read_text()) if f.exists() else []


def read_trust():
    f = Path("memory/trust_scores.json")
    return json.loads(f.read_text()) if f.exists() else {}


def read_automerge_log():
    f = Path("memory/automerge_log.json")
    return json.loads(f.read_text()) if f.exists() else []


def read_validation_log():
    f = Path("memory/validation_log.json")
    return json.loads(f.read_text()) if f.exists() else []


def read_analytics_intelligence():
    f = Path("memory/analytics_intelligence.json")
    return json.loads(f.read_text()) if f.exists() else {}


def read_visual_qa_summary():
    f = Path("memory/visual_qa_summary.json")
    return json.loads(f.read_text()) if f.exists() else {}


def read_self_improvement():
    f = Path("memory/self_improvement_report.json")
    if not f.exists():
        return {}
    data = json.loads(f.read_text())
    # Return only the dashboard-relevant fields (not raw_metrics which is large)
    return {
        "generated_at": data.get("generated_at", ""),
        "overall_health_score": data.get("overall_health_score", 0),
        "health_summary": data.get("health_summary", ""),
        "efficiency_score": data.get("efficiency_score", 0),
        "quality_score": data.get("quality_score", 0),
        "velocity_score": data.get("velocity_score", 0),
        "top_improvements": data.get("top_improvements", [])[:8],
        "cost_projection": data.get("cost_projection", {}),
        "next_cycle_focus": data.get("next_cycle_focus", ""),
        "raw_metrics": data.get("raw_metrics", {}),
        "ai_generated": data.get("ai_generated", False),
        "tokens_used": data.get("tokens_used", 0),
        "cost_usd": data.get("cost_usd", 0.0),
    }


def read_json(path: str, default=None):
    f = Path(path)
    if not f.exists():
        return default if default is not None else {}
    try:
        return json.loads(f.read_text())
    except Exception:
        return default if default is not None else {}


def read_memory_summary():
    return read_json("memory/memory_summary.json")


def read_browser_qa_summary():
    return read_json("memory/browser_qa_summary.json")


def read_ai_qa_summary():
    return read_json("memory/ai_qa_summary.json")


def read_deployment_monitor():
    return read_json("memory/deployment_monitor.json")


def read_execution_summary():
    return read_json("memory/execution_summary.json")


def read_revenue_report():
    data = read_json("memory/revenue_report.json")
    if not data:
        return {}
    # Strip all_features arrays (large) from project breakdowns
    projects = {}
    for proj, pdata in data.get("projects", {}).items():
        projects[proj] = {k: v for k, v in pdata.items() if k != "all_features"}
    return {
        "generated_at": data.get("generated_at", ""),
        "portfolio_summary": data.get("portfolio_summary", {}),
        "ai_analysis": data.get("ai_analysis", {}),
        "projects": projects,
    }


def read_swarm_summary():
    return read_json("memory/swarm_summary.json")


def read_cross_project_summary():
    return read_json("memory/cross_project_summary.json")


def read_strategy_report():
    data = read_json("memory/strategy_report.json")
    if not data:
        return {}
    plan = data.get("strategic_plan", {})
    return {
        "generated_at": data.get("generated_at", ""),
        "bottlenecks": data.get("bottlenecks", []),
        "executor_items_injected": data.get("executor_items_injected", 0),
        "strategic_plan": {
            "strategic_summary": plan.get("strategic_summary", ""),
            "north_star_metric": plan.get("north_star_metric", ""),
            "30_day_plan": plan.get("30_day_plan", {}),
            "90_day_plan": plan.get("90_day_plan", {}),
            "priority_matrix": plan.get("priority_matrix", [])[:10],
            "roi_forecasts": plan.get("roi_forecasts", {}),
        },
    }


def read_market_intelligence():
    data = read_json("memory/market_intelligence.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "trending_topics": data.get("trending_topics", {}),
        "keyword_gaps": data.get("keyword_gaps", {}),
        "new_monetization_angles": data.get("new_monetization_angles", {}),
        "competitive_gaps": data.get("competitive_gaps", {}),
        "competitors": {
            proj: [
                {k: v for k, v in c.items()}
                for c in comps
            ]
            for proj, comps in data.get("competitors", {}).items()
        },
    }


def read_priority_report():
    return read_json("memory/priority_report.json")


def read_experiment_summary():
    return read_json("memory/experiment_summary.json")


def read_evolution_report():
    data = read_json("memory/evolution_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "system_maturity_score": data.get("system_maturity_score", 0),
        "evolution_summary": data.get("evolution_summary", ""),
        "next_evolution_priority": data.get("next_evolution_priority", ""),
        "recommended_evolutions": data.get("recommended_evolutions", [])[:8],
        "prompt_improvements": data.get("prompt_improvements", [])[:5],
        "threshold_recommendations": data.get("threshold_recommendations", {}),
        "architecture_recommendations": data.get("architecture_recommendations", []),
        "token_optimization": data.get("token_optimization", {}),
        "applied_evolutions": data.get("applied_evolutions", []),
    }


def read_web_intelligence():
    data = read_json("memory/web_intelligence.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "competitors": {
            proj: [
                {k: v for k, v in c.items() if k != "pages"}
                for c in comps
            ]
            for proj, comps in data.get("competitors", {}).items()
        },
        "hn_stories": data.get("hn_stories", [])[:10],
        "reddit_posts": data.get("reddit_posts", [])[:10],
        "github_trending": data.get("github_trending", [])[:10],
        "opportunities": data.get("opportunities", {}),
    }


def read_seo_opportunities():
    data = read_json("memory/seo_opportunities.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "total_addressable_traffic": data.get("total_addressable_traffic", 0),
        "executor_items_injected": data.get("executor_items_injected", 0),
        "execution_queue": data.get("execution_queue", [])[:15],
        "projects": {
            proj: {
                "topical_clusters": clusters.get("topical_clusters", [])[:5],
                "long_tail_opportunities": clusters.get("long_tail_opportunities", [])[:5],
                "quick_wins": clusters.get("quick_wins", [])[:5],
                "total_addressable_traffic": clusters.get("total_addressable_traffic", 0),
            }
            for proj, clusters in data.get("projects", {}).items()
        },
    }


def read_competitor_memory():
    data = read_json("memory/competitor_memory.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "total_competitors": data.get("total_competitors", 0),
        "reachable_competitors": data.get("reachable_competitors", 0),
        "all_recommendations": data.get("all_recommendations", {}),
        "projects": {
            proj: {
                "patterns": pd.get("patterns", {}),
                "profiled_at": pd.get("profiled_at", ""),
                "profiles": [
                    {k: v for k, v in p.items() if k not in ("raw_html",)}
                    for p in pd.get("profiles", [])
                ],
            }
            for proj, pd in data.get("projects", {}).items()
        },
    }


def read_social_signals():
    data = read_json("memory/social_signals.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "total_posts_analyzed": data.get("total_posts_analyzed", 0),
        "cross_project": data.get("cross_project", {}),
        "projects": {
            proj: {
                "signal_strength": pd.get("signal_strength", 0),
                "post_count": pd.get("post_count", 0),
                "trending_keywords": pd.get("trending_keywords", [])[:10],
                "sentiment_analysis": pd.get("sentiment_analysis", {}),
                "github_trending": pd.get("github_trending", [])[:5],
                "top_posts": pd.get("top_posts", [])[:5],
            }
            for proj, pd in data.get("projects", {}).items()
        },
    }


def read_traffic_intelligence():
    data = read_json("memory/traffic_intelligence.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "total_addressable_6mo": data.get("total_addressable_6mo", 0),
        "projects": {
            proj: {
                "our_est_monthly_visits": pd.get("our_est_monthly_visits", 0),
                "traffic_gaps": pd.get("traffic_gaps", []),
                "seasonal": pd.get("seasonal", {}),
                "ctr_opportunities": pd.get("ctr_opportunities", [])[:8],
                "ai_analysis": pd.get("ai_analysis", {}),
            }
            for proj, pd in data.get("projects", {}).items()
        },
    }


def read_monetization_report():
    data = read_json("memory/monetization_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "portfolio_monthly_lift_usd": data.get("portfolio_monthly_lift_usd", 0),
        "portfolio_annual_lift_usd": data.get("portfolio_annual_lift_usd", 0),
        "projects": {
            proj: {
                "model": pd.get("model", ""),
                "gaps_detected": pd.get("gaps_detected", []),
                "revenue_lift": pd.get("revenue_lift", {}),
                "monetization_plan": pd.get("monetization_plan", {}),
            }
            for proj, pd in data.get("projects", {}).items()
        },
    }


def read_campaign_report():
    data = read_json("memory/campaign_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "total_pages_generated": data.get("total_pages_generated", 0),
        "executor_items_injected": data.get("executor_items_injected", 0),
        "projects": {
            proj: {
                "campaigns": [
                    {k: v for k, v in c.items() if k != "html"}
                    for c in pd.get("campaigns", [])
                ],
                "launch_sequence": pd.get("launch_sequence", []),
            }
            for proj, pd in data.get("projects", {}).items()
        },
    }


def read_realtime_alerts():
    data = read_json("memory/realtime_alerts.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "posts_scanned": data.get("posts_scanned", 0),
        "events_detected": data.get("events_detected", 0),
        "new_events": data.get("new_events", 0),
        "alert_level": data.get("alert_level", "normal"),
        "executor_items_injected": data.get("executor_items_injected", 0),
        "analysis": data.get("analysis", {}),
        "events": data.get("events", [])[:10],
    }


def read_knowledge_graph():
    data = read_json("memory/knowledge_graph.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "metrics": data.get("metrics", {}),
        "insights": data.get("insights", {}),
        "nodes": data.get("nodes", [])[:50],
        "edges": data.get("edges", [])[:100],
    }


def read_growth_report():
    data = read_json("memory/growth_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "portfolio_growth_score": data.get("portfolio_growth_score", 0),
        "total_backlink_opportunities": data.get("total_backlink_opportunities", 0),
        "total_schema_opportunities": data.get("total_schema_opportunities", 0),
        "all_quick_wins": data.get("all_quick_wins", [])[:8],
        "projects": {
            pid: {
                "domain": pdata.get("domain", ""),
                "niche": pdata.get("niche", ""),
                "growth_score": pdata.get("growth_score", 0),
                "backlink_opportunities": pdata.get("backlink_opportunities", [])[:4],
                "topical_authority_plan": pdata.get("topical_authority_plan", [])[:4],
                "schema_opportunities": pdata.get("schema_opportunities", [])[:4],
                "high_ctr_pages": pdata.get("high_ctr_pages", [])[:4],
                "indexing_status": pdata.get("indexing_status", {}),
                "ai_strategy": pdata.get("ai_strategy", {}),
            }
            for pid, pdata in data.get("projects", {}).items()
        },
    }


def read_monetization_runtime_report():
    data = read_json("memory/monetization_runtime_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "portfolio_current_revenue_usd": data.get("portfolio_current_revenue_usd", 0),
        "portfolio_target_revenue_usd": data.get("portfolio_target_revenue_usd", 0),
        "portfolio_revenue_gap_usd": data.get("portfolio_revenue_gap_usd", 0),
        "projects": {
            pid: {
                "model": pdata.get("model", ""),
                "current_revenue_est_usd": pdata.get("current_revenue_est_usd", 0),
                "monthly_target_usd": pdata.get("monthly_target_usd", 0),
                "revenue_gap_usd": pdata.get("revenue_gap_usd", 0),
                "rpm_estimates": pdata.get("rpm_estimates", {}),
                "implementations": pdata.get("implementations", {}),
                "ai_plan": pdata.get("ai_plan", {}),
            }
            for pid, pdata in data.get("projects", {}).items()
        },
    }


def read_conversion_report():
    data = read_json("memory/conversion_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "portfolio_cro_score": data.get("portfolio_cro_score", 0),
        "projects": {
            pid: {
                "model": pdata.get("model", ""),
                "primary_conversion": pdata.get("primary_conversion", ""),
                "conversion_gaps": pdata.get("conversion_gaps", []),
                "cta_optimization": pdata.get("cta_optimization", {}),
                "funnel_analysis": pdata.get("funnel_analysis", {}),
                "revenue_per_visit": pdata.get("revenue_per_visit", {}),
                "ai_recommendations": pdata.get("ai_recommendations", {}),
            }
            for pid, pdata in data.get("projects", {}).items()
        },
    }


def read_acquisition_report():
    data = read_json("memory/acquisition_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "portfolio_month_1_session_target": data.get("portfolio_month_1_session_target", 0),
        "portfolio_month_3_session_target": data.get("portfolio_month_3_session_target", 0),
        "projects": {
            pid: {
                "viral_content_plan": pdata.get("viral_content_plan", [])[:4],
                "seo_cluster_expansion": pdata.get("seo_cluster_expansion", {}),
                "social_campaign": pdata.get("social_campaign", {}),
                "growth_loops": pdata.get("growth_loops", [])[:4],
                "outreach_plan": pdata.get("outreach_plan", [])[:4],
                "launch_sequence": pdata.get("launch_sequence", []),
                "ai_strategy": pdata.get("ai_strategy", {}),
            }
            for pid, pdata in data.get("projects", {}).items()
        },
    }


def read_scaling_report():
    data = read_json("memory/scaling_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "storage": data.get("storage", {}),
        "token_usage": data.get("token_usage", {}),
        "workload_balance": data.get("workload_balance", {}),
        "optimizations": data.get("optimizations", []),
        "ai_analysis": data.get("ai_analysis", {}),
    }


def read_programmatic_seo_report():
    data = read_json("memory/programmatic_seo_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "total_pages_generated": data.get("total_pages_generated", 0),
        "hub_pages_count": data.get("hub_pages_count", 0),
        "long_tail_pages_count": data.get("long_tail_pages_count", 0),
        "faq_pages_count": data.get("faq_pages_count", 0),
        "comparison_pages_count": data.get("comparison_pages_count", 0),
        "trending_pages_count": data.get("trending_pages_count", 0),
        "estimated_monthly_traffic_gain": data.get("estimated_monthly_traffic_gain", 0),
        "seo_score": data.get("seo_score", 0),
        "top_opportunities": data.get("top_opportunities", []),
        "next_priorities": data.get("next_priorities", []),
        "authority_building_status": data.get("authority_building_status", ""),
        "executive_summary": data.get("executive_summary", ""),
    }


def read_product_builder_report():
    data = read_json("memory/product_builder_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "features_built": data.get("features_built", 0),
        "has_real_market_data": data.get("has_real_market_data", False),
        "bist_symbols_tracked": data.get("bist_symbols_tracked", 0),
        "crypto_tracked": data.get("crypto_tracked", 0),
        "stock_analyses": data.get("stock_analyses", 0),
        "portfolio_features": data.get("portfolio_features", 0),
        "alert_types": data.get("alert_types", 0),
        "product_roadmap": data.get("product_roadmap", []),
        "bist_market_page": {
            "market_sentiment": (data.get("bist_market_page") or {}).get("market_sentiment", ""),
            "sentiment_reason": (data.get("bist_market_page") or {}).get("sentiment_reason", ""),
            "top_gainers": (data.get("bist_market_page") or {}).get("top_gainers", [])[:5],
            "top_losers": (data.get("bist_market_page") or {}).get("top_losers", [])[:3],
            "watch_list_picks": (data.get("bist_market_page") or {}).get("watch_list_picks", [])[:3],
        },
        "crypto_movers": {
            "top_movers": (data.get("crypto_movers") or {}).get("top_movers", [])[:5],
            "market_dominance": (data.get("crypto_movers") or {}).get("market_dominance", {}),
            "fear_greed_index": (data.get("crypto_movers") or {}).get("fear_greed_index", {}),
        },
    }


def read_client_acquisition_report():
    data = read_json("memory/client_acquisition_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "pricing_tiers": data.get("pricing_tiers", 0),
        "service_pages": data.get("service_pages", 0),
        "case_studies": data.get("case_studies", 0),
        "lead_magnets": data.get("lead_magnets", 0),
        "seo_clusters": data.get("seo_clusters", 0),
        "estimated_monthly_leads": data.get("estimated_monthly_leads", 0),
        "estimated_pipeline_value_usd": data.get("estimated_pipeline_value_usd", 0),
        "conversion_funnel": data.get("conversion_funnel", []),
    }


def read_analytics_syncer_report():
    data = read_json("memory/analytics_syncer_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "sources_connected": data.get("sources_connected", []),
        "sources_count": data.get("sources_count", 0),
        "analytics_health_score": data.get("analytics_health_score", 0),
        "data_completeness": data.get("data_completeness", "low"),
        "revenue_insights": data.get("revenue_insights", {}),
        "traffic_insights": data.get("traffic_insights", {}),
        "optimization_priorities": data.get("optimization_priorities", []),
        "stripe": data.get("stripe", {"status": "not_connected"}),
        "adsense": data.get("adsense", {"status": "not_connected"}),
        "project_analytics": {
            pk: {
                "cloudflare": pdata.get("cloudflare", {}),
                "posthog": pdata.get("posthog", {}),
                "baseline": pdata.get("baseline", {}),
            }
            for pk, pdata in data.get("project_analytics", {}).items()
        },
    }


def read_revenue_tracker_report():
    data = read_json("memory/revenue_tracker_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "portfolio": data.get("portfolio", {}),
        "projects": data.get("projects", {}),
        "revenue_score": data.get("revenue_score", 0),
        "attainment_status": data.get("attainment_status", ""),
        "critical_revenue_actions": data.get("critical_revenue_actions", [])[:5],
        "rpm_optimization": data.get("rpm_optimization", {}),
        "conversion_opportunities": data.get("conversion_opportunities", []),
        "highest_roi_action": data.get("highest_roi_action", ""),
        "profitability_ranking": data.get("profitability_ranking", []),
        "executive_summary": data.get("executive_summary", ""),
        "recent_history": data.get("recent_history", [])[-7:],
    }


def read_page_deployer_report():
    data = read_json("memory/page_deployer_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "cycle_deployed": data.get("cycle_deployed", 0),
        "cycle_failed": data.get("cycle_failed", 0),
        "queue_remaining": data.get("queue_remaining", 0),
        "total_deployed_all_time": data.get("total_deployed_all_time", 0),
        "deployed_this_cycle": data.get("deployed_this_cycle", []),
        "failed_this_cycle": data.get("failed_this_cycle", []),
        "deployment_score": data.get("deployment_score", 0),
        "cycle_status": data.get("cycle_status", ""),
        "recommendations": data.get("recommendations", []),
    }


def read_roi_prioritizer_report():
    data = read_json("memory/roi_prioritizer_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "total_actions_ranked": data.get("total_actions_ranked", 0),
        "total_pipeline_usd": data.get("total_pipeline_usd", 0),
        "strategy_score": data.get("strategy_score", 0),
        "top_priority_action": data.get("top_priority_action", ""),
        "execution_philosophy": data.get("execution_philosophy", ""),
        "execution_queue": data.get("execution_queue", {}),
        "top_20_actions": data.get("top_20_actions", [])[:20],
        "weekly_sprint_focus": data.get("weekly_sprint_focus", []),
        "revenue_unlock_sequence": data.get("revenue_unlock_sequence", []),
        "agent_directives": data.get("agent_directives", {}),
        "risk_flags": data.get("risk_flags", []),
        "executive_summary": data.get("executive_summary", ""),
    }


def read_kpi_report():
    data = read_json("memory/kpi_report.json")
    if not data:
        return {}
    projects_out = {}
    for pk, pdata in data.get("projects", {}).items():
        kpis = pdata.get("kpis", {})
        projects_out[pk] = {
            "kpis": kpis,
            "avg_attainment_pct": pdata.get("avg_attainment_pct", 0),
            "kpi_health_score": pdata.get("kpi_health_score", 0),
            "alerts": pdata.get("alerts", []),
            "on_track_count": pdata.get("on_track_count", 0),
            "total_kpis": pdata.get("total_kpis", 0),
            "actuals": pdata.get("actuals", {}),
        }
    return {
        "generated_at": data.get("generated_at", ""),
        "portfolio": data.get("portfolio", {}),
        "projects": projects_out,
        "kpi_score": data.get("kpi_score", 0),
        "executive_summary": data.get("executive_summary", ""),
        "critical_kpis": data.get("critical_kpis", []),
        "quick_wins": data.get("quick_wins", []),
        "growth_momentum": data.get("growth_momentum", "stable"),
        "forecast_30_days": data.get("forecast_30_days", {}),
        "kpi_priorities": data.get("kpi_priorities", []),
        "recent_history": data.get("recent_history", [])[-14:],
        "goals": data.get("goals", {}),
        "ai_analysis": data.get("ai_analysis", {}),
    }


def read_deployment_pipeline_report():
    data = read_json("memory/deployment_pipeline_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "projects_monitored": data.get("projects_monitored", 0),
        "healthy_projects": data.get("healthy_projects", 0),
        "projects": {
            pk: {
                "domain": pdata.get("domain", ""),
                "health_score": pdata.get("health_score", 0),
                "availability": pdata.get("availability", {}),
                "cwv": pdata.get("cwv", {}),
                "rollback_triggers": pdata.get("rollback_triggers", []),
                "recommendations": pdata.get("recommendations", [])[:5],
                "ai_health_status": pdata.get("ai_health_status", ""),
            }
            for pk, pdata in data.get("projects", {}).items()
        },
        "ai_analysis": data.get("ai_analysis", {}),
    }


def read_vector_memory_stats():
    data = read_json("memory/vector_stats.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "total_memories": data.get("total_memories", 0),
        "embedded_memories": data.get("embedded_memories", 0),
        "embedding_coverage_pct": data.get("embedding_coverage_pct", 0),
        "memories_by_type": data.get("memories_by_type", {}),
        "memories_pruned": data.get("memories_pruned", 0),
        "total_tokens": data.get("total_tokens", 0),
        "total_cost_usd": data.get("total_cost_usd", 0.0),
        "index_size": data.get("index_size", 0),
    }


def read_retrieval_results():
    data = read_json("memory/retrieval_results.json")
    if not data:
        return {}
    results = {}
    for qid, qdata in data.get("results", {}).items():
        memories = [
            {k: v for k, v in m.items() if k != "embedding"}
            for m in qdata.get("memories", [])[:5]
        ]
        results[qid] = {
            "query": qdata.get("query", ""),
            "memory_count": qdata.get("memory_count", 0),
            "synthesis": qdata.get("synthesis", ""),
            "memories": memories,
        }
    return {
        "generated_at": data.get("generated_at", ""),
        "queries_run": data.get("queries_run", 0),
        "total_memories_retrieved": data.get("total_memories_retrieved", 0),
        "index_size": data.get("index_size", 0),
        "embedded_memories": data.get("embedded_memories", 0),
        "results": results,
        "context_payload": data.get("context_injection_payload", {}),
    }


def read_tool_runtime_report():
    data = read_json("memory/tool_runtime_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "tools_registered": data.get("tools_registered", 0),
        "tools_executed_this_cycle": data.get("tools_executed_this_cycle", 0),
        "tools_succeeded": data.get("tools_succeeded", 0),
        "tools_failed": data.get("tools_failed", 0),
        "tool_catalog": data.get("tool_catalog", []),
        "execution_log": data.get("execution_log", [])[:20],
        "ai_analysis": data.get("ai_analysis", {}),
    }


def read_research_report():
    data = read_json("memory/research_report.json")
    if not data:
        return {}
    projects = {}
    for pk, pdata in data.get("projects", {}).items():
        signals = []
        for sig in pdata.get("competitor_signals", []):
            signals.append({k: v for k, v in sig.items() if k not in ("content_length",)})
        projects[pk] = {
            "niche": pdata.get("niche", ""),
            "competitors_researched": pdata.get("competitors_researched", []),
            "competitor_signals": signals,
            "ranking_opportunities": pdata.get("ranking_opportunities", {}),
            "ux_comparison": pdata.get("ux_comparison", {}),
            "monetization_benchmark": pdata.get("monetization_benchmark", {}),
            "ai_synthesis": pdata.get("ai_synthesis", {}),
        }
    return {
        "generated_at": data.get("generated_at", ""),
        "projects_researched": data.get("projects_researched", 0),
        "total_competitors_analyzed": data.get("total_competitors_analyzed", 0),
        "emerging_technologies": data.get("emerging_technologies", {}),
        "projects": projects,
    }


def read_sandbox_report():
    data = read_json("memory/sandbox_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "active_sandboxes": data.get("active_sandboxes", 0),
        "expired_this_cycle": data.get("expired_this_cycle", 0),
        "checkpoints_created": data.get("checkpoints_created", 0),
        "experiment_templates": data.get("experiment_templates", []),
        "active_sandbox_list": data.get("active_sandbox_list", []),
        "new_sandbox": data.get("new_sandbox"),
        "ai_recommendations": data.get("ai_recommendations", {}),
    }


def read_observability_report():
    data = read_json("memory/observability_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "observability_score": data.get("observability_score", 0),
        "operational_status": data.get("operational_status", "unknown"),
        "fresh_workflow_count": data.get("fresh_workflow_count", 0),
        "stale_workflow_count": data.get("stale_workflow_count", 0),
        "workflow_metrics": data.get("workflow_metrics", []),
        "ai_latency_estimates": data.get("ai_latency_estimates", [])[:10],
        "total_tracked_ai_cost_usd": data.get("total_tracked_ai_cost_usd", 0.0),
        "bottlenecks": data.get("bottlenecks", []),
        "agent_heatmap": data.get("agent_heatmap", {}),
        "error_propagation": data.get("error_propagation", []),
        "memory_retrieval_performance": data.get("memory_retrieval_performance", {}),
        "ai_analysis": data.get("ai_analysis", {}),
    }


def read_agent_bus():
    data = read_json("memory/agent_bus.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "active_agents": data.get("active_agents", []),
        "total_events": data.get("total_events", 0),
        "tasks_routed": data.get("tasks_routed", 0),
        "delegations": data.get("delegations", 0),
        "escalations": data.get("escalations", 0),
        "bus_health": data.get("bus_health", {}),
        "event_queue": data.get("event_queue", [])[:10],
        "task_queue": data.get("task_queue", [])[:10],
    }


def read_cognition_report():
    data = read_json("memory/cognition_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "health_score": data.get("health_score", 0),
        "cognition_cycle": data.get("cognition_cycle", {}),
        "reflection": data.get("reflection", {}),
        "latest_chain": data.get("latest_chain", {}),
        "long_horizon_plan": data.get("long_horizon_plan", {}),
    }


def read_governance_report():
    data = read_json("memory/governance_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "mode": data.get("mode", ""),
        "approved_actions": data.get("approved_actions", 0),
        "blocked_actions": data.get("blocked_actions", 0),
        "deferred_actions": data.get("deferred_actions", 0),
        "risk_score_avg": data.get("risk_score_avg", 0),
        "ai_review": data.get("ai_review", {}),
        "decisions": data.get("decisions", [])[:10],
    }


def read_runtime_report():
    data = read_json("memory/runtime_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "tasks_dispatched": data.get("tasks_dispatched", 0),
        "tasks_completed": data.get("tasks_completed", 0),
        "tasks_failed": data.get("tasks_failed", 0),
        "tasks_retried": data.get("tasks_retried", 0),
        "workload_balance": data.get("workload_balance", {}),
        "ai_analysis": data.get("ai_analysis", {}),
    }


def read_task_economy_report():
    data = read_json("memory/task_economy_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "portfolio": data.get("portfolio", {}),
        "top_tasks": data.get("top_tasks", [])[:10],
        "by_project": data.get("by_project", {}),
        "ai_analysis": data.get("ai_analysis", {}),
    }


def read_agent_evolution_report():
    data = read_json("memory/agent_evolution_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "evolution_results": data.get("evolution_results", {}),
        "hierarchy": data.get("hierarchy", {}),
        "avg_composite_score": data.get("avg_composite_score", 0),
        "top_performer": data.get("top_performer", ""),
        "most_improved": data.get("most_improved", ""),
    }


def read_kernel_report():
    data = read_json("memory/kernel_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "company_mode": data.get("company_mode", ""),
        "mode_info": data.get("mode_info", {}),
        "ops_score": data.get("ops_score", 0),
        "bottlenecks": data.get("bottlenecks", []),
        "swarm_activity": data.get("swarm_activity", {}),
        "token_flow": data.get("token_flow", {}),
        "agent_states": data.get("agent_states", {}),
        "ai_analysis": data.get("ai_analysis", {}),
        "execution_graph": data.get("execution_graph", {}),
    }


def read_roadmap():
    data = read_json("memory/roadmap.json")
    if not data:
        return {}
    # Return only dashboard-relevant fields (not full HTML content)
    return {
        "generated_at": data.get("generated_at", ""),
        "total_items": data.get("total_items", 0),
        "total_cost_usd": data.get("total_cost_usd", 0.0),
        "cross_project": {
            k: v for k, v in data.get("cross_project", {}).items()
            if k in ("portfolio_summary", "resource_allocation", "consolidated_priority_queue",
                     "cross_project_patterns", "shared_opportunities", "next_sprint_plan")
        },
        "consolidated_priority_queue": data.get("consolidated_priority_queue", [])[:20],
        "projects": {
            proj: {
                "summary": pdata.get("summary", ""),
                "quick_wins": pdata.get("quick_wins", [])[:3],
                "90_day_goal": pdata.get("90_day_goal", ""),
                "seo_gaps": pdata.get("seo_gaps", [])[:5],
                "feature_gaps": pdata.get("feature_gaps", [])[:5],
                "ux_gaps": pdata.get("ux_gaps", [])[:3],
                "monetization_opportunities": pdata.get("monetization_opportunities", [])[:3],
                "priority_queue": pdata.get("priority_queue", [])[:8],
            }
            for proj, pdata in data.get("projects", {}).items()
        },
    }


def read_product_outputs():
    """Read all product execution output records from outputs/{project}/product/."""
    records = []
    for proj_dir in Path("outputs").iterdir():
        if not proj_dir.is_dir() or proj_dir.name.startswith("."):
            continue
        product_dir = proj_dir / "product"
        if not product_dir.exists():
            continue
        for f in product_dir.glob("*.json"):
            try:
                records.append(json.loads(f.read_text()))
            except Exception:
                pass
    records.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
    return records


def build_product_metrics(product_outputs):
    if not product_outputs:
        return {
            "total_features": 0, "pages_generated": 0, "widgets_generated": 0,
            "est_monthly_seo_visits": 0, "total_tokens": 0, "total_cost_usd": 0.0,
            "by_project": {}, "by_type": {}, "recent_features": [],
        }
    pages = sum(1 for o in product_outputs if o.get("feature_type") in ("page", "category_page", "seo_hub"))
    widgets = sum(1 for o in product_outputs if o.get("estimated_widgets", 0) > 0)
    est_visits = sum(o.get("estimated_monthly_visits", 0) for o in product_outputs)
    by_project, by_type = {}, {}
    for o in product_outputs:
        p = o.get("project", "unknown")
        t = o.get("feature_type", "unknown")
        by_project[p] = by_project.get(p, 0) + 1
        by_type[t] = by_type.get(t, 0) + 1
    return {
        "total_features": len(product_outputs),
        "pages_generated": pages,
        "widgets_generated": widgets,
        "est_monthly_seo_visits": est_visits,
        "total_tokens": sum(o.get("tokens_used", 0) for o in product_outputs),
        "total_cost_usd": round(sum(o.get("cost_usd", 0.0) for o in product_outputs), 6),
        "by_project": by_project,
        "by_type": by_type,
        "recent_features": [
            {
                "label": o.get("label"),
                "project": o.get("project"),
                "feature_type": o.get("feature_type"),
                "target_path": o.get("target_path"),
                "seo_target": o.get("seo_target"),
                "est_monthly_visits": o.get("estimated_monthly_visits", 0),
                "est_widgets": o.get("estimated_widgets", 0),
                "bytes_generated": o.get("bytes_generated", 0),
                "tokens_used": o.get("tokens_used", 0),
                "pr_url": o.get("pr_url"),
                "generated_at": o.get("generated_at"),
            }
            for o in product_outputs[:30]
        ],
    }


def build_loops(outputs):
    by_project = {}
    for o in outputs:
        p = o.get("project", "")
        by_project.setdefault(p, []).append(o)

    loops = []
    for defn in LOOPS:
        proj_outs = by_project.get(defn["project"], [])
        last = proj_outs[0] if proj_outs else None
        last_run = (last or {}).get("generated_at")

        next_run = None
        if last_run:
            try:
                dt = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                next_run = (dt + timedelta(minutes=defn["interval_minutes"])).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

        loops.append({
            **defn,
            "last_run": last_run,
            "last_status": "completed" if last else "pending",
            "run_count": len(proj_outs),
            "success_count": sum(1 for o in proj_outs if o.get("ai_generated")),
            "next_run_scheduled": next_run,
        })

    active = sum(1 for l in loops if l["last_status"] == "completed")
    return loops, active


def build_ai_analytics(outputs):
    ai_outs = [o for o in outputs if o.get("ai_generated")]
    total = len(outputs)
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    by_provider, by_project, by_op, by_day = {}, {}, {}, {}

    for o in outputs:
        proj = o.get("project", "unknown")
        op = o.get("operation_type", "unknown")
        prov = o.get("ai_provider", "openai") if o.get("ai_generated") else None

        by_project[proj] = by_project.get(proj, 0) + 1
        by_op[op] = by_op.get(op, 0) + 1

        if prov:
            if prov not in by_provider:
                by_provider[prov] = {"requests": 0, "tokens": 0, "cost_usd": 0.0, "success_rate": 100, "avg_latency_ms": 0}
            by_provider[prov]["requests"] += 1
            by_provider[prov]["tokens"] += o.get("tokens_used", 0)
            by_provider[prov]["cost_usd"] += o.get("cost_usd", 0.0)

        try:
            dt = datetime.fromisoformat(o.get("generated_at", "").replace("Z", "+00:00"))
            if dt >= cutoff:
                day = dt.strftime("%Y-%m-%d")
                if day not in by_day:
                    by_day[day] = {"requests": 0, "success": 0, "cost_usd": 0.0}
                by_day[day]["requests"] += 1
                if o.get("ai_generated"):
                    by_day[day]["success"] += 1
                by_day[day]["cost_usd"] += o.get("cost_usd", 0.0)
        except Exception:
            pass

    total_tokens = sum(o.get("tokens_used", 0) for o in outputs)
    total_cost = sum(o.get("cost_usd", 0.0) for o in outputs)
    ai_count = len(ai_outs)

    return {
        "total_calls": total,
        "successful_calls": ai_count,
        "rate_limited_calls": 0,
        "success_rate_pct": round(ai_count / max(total, 1) * 100),
        "ai_generated_pct": round(ai_count / max(total, 1) * 100),
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "by_provider": by_provider,
        "by_project": by_project,
        "by_operation_type": by_op,
        "by_day": by_day,
    }


def read_game_factory_report():
    data = read_json("memory/game_factory_report.json")
    if not data:
        data = read_json("memory/game_factory/factory_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "total_generated": data.get("total_generated", 0),
        "total_eligible": data.get("total_eligible", 0),
        "pass_rate": data.get("pass_rate", "0%"),
        "avg_qa_score": data.get("avg_qa_score", 0),
        "total_cost_usd": data.get("total_cost_usd", 0.0),
        "total_tokens": data.get("total_tokens", 0),
        "games": [
            {k: v for k, v in g.items() if k not in ("html",)}
            for g in data.get("games", [])[:20]
        ],
        "by_type": data.get("by_type", {}),
        "eligible_games": data.get("eligible_games", []),
    }


def read_game_seo_report():
    data = read_json("memory/game_seo_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "seo_pages_count": data.get("seo_pages_count", 0),
        "category_hubs_count": data.get("category_hubs_count", 0),
        "total_keywords": data.get("total_keywords", 0),
        "total_cost_usd": data.get("total_cost_usd", 0.0),
        "top_games": data.get("top_games", [])[:10],
        "hub_types": data.get("hub_types", []),
    }


def read_game_qa_report():
    data = read_json("memory/game_qa_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "summary": data.get("summary", {}),
        "games": [
            {k: v for k, v in g.items() if k not in ("checks",)}
            for g in data.get("games", [])[:20]
        ],
    }


def read_admin_governance_report():
    data = read_json("memory/admin_governance_report.json")
    if not data:
        return {}
    queue = data.get("queue", {})
    return {
        "generated_at": data.get("generated_at", ""),
        "counts": queue.get("counts", {}),
        "pending": queue.get("pending", [])[:10],
        "qa_eligible": queue.get("qa_eligible", [])[:10],
        "approved": queue.get("approved", [])[:10],
        "deployed": queue.get("deployed", [])[:10],
        "rejected": queue.get("rejected", [])[:5],
        "ai_summary": data.get("ai_summary", {}),
        "recent_audit": data.get("recent_audit", [])[-10:],
    }


def read_indexing_report():
    data = read_json("memory/indexing_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "auth_mode": data.get("auth_mode", "none"),
        "credentials_configured": data.get("credentials_configured", False),
        "queue_size": data.get("queue_size", 0),
        "total_indexed_all_time": data.get("total_indexed_all_time", 0),
        "indexed_today": data.get("indexed_today", 0),
        "failed_count": data.get("failed_count", 0),
        "daily_quota": data.get("daily_quota", 200),
        "quota_used_today": data.get("quota_used_today", 0),
        "quota_remaining": data.get("quota_remaining", 200),
        "success_rate": data.get("success_rate", "N/A"),
        "queue_by_priority": data.get("queue_by_priority", {}),
        "recent_indexed": data.get("recent_indexed", [])[:15],
        "recent_failed": data.get("recent_failed", [])[:10],
        "queue_preview": data.get("queue_preview", [])[:10],
    }


def read_publishing_pipeline_report():
    data = read_json("memory/publishing_pipeline_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "total_games": data.get("total_games", 0),
        "pending_approval": data.get("pending_approval", 0),
        "approved": data.get("approved", 0),
        "deployed": data.get("deployed", 0),
        "pipeline_health": data.get("pipeline_health", "unknown"),
        "bottleneck_step": data.get("bottleneck_step", ""),
        "throughput_estimate": data.get("throughput_estimate", ""),
        "monetization": data.get("monetization", {}),
        "seo_velocity": data.get("seo_velocity", "normal"),
        "top_priorities": data.get("top_priorities", []),
        "step_summary": data.get("step_summary", {}),
        "games": data.get("games", [])[:25],
    }


def read_game_asset_report():
    data = read_json("memory/game_asset_report.json")
    if not data:
        return {}
    return {
        "generated_at": data.get("generated_at", ""),
        "games_processed": data.get("games_processed", 0),
        "categories_processed": data.get("categories_processed", 0),
        "total_assets_generated": data.get("total_assets_generated", 0),
        "category_banners": list(data.get("category_banners", {}).keys()),
        "game_assets": [
            {"game_id": a.get("game_id"), "game_type": a.get("game_type"),
             "name_en": a.get("name_en"), "assets": list(a.get("assets", {}).keys())}
            for a in data.get("game_assets", [])[:20]
        ],
    }


def read_telegram_logs():
    data = read_json("memory/telegram_logs.json")
    if not data:
        return {}
    return {
        "updated_at": data.get("updated_at", ""),
        "total_sent": data.get("total_sent", 0),
        "entries": data.get("entries", [])[-30:],
    }


def main():
    print("[dashboard] Aggregating dashboard data...")

    outputs = read_outputs()
    prs = read_prs()
    trust = read_trust()
    automerge_log = read_automerge_log()
    validation_log = read_validation_log()
    product_outputs = read_product_outputs()
    product_metrics = build_product_metrics(product_outputs)
    analytics_intel = read_analytics_intelligence()
    visual_qa = read_visual_qa_summary()
    self_improvement = read_self_improvement()
    memory_summary = read_memory_summary()
    browser_qa = read_browser_qa_summary()
    ai_qa = read_ai_qa_summary()
    deployment_monitor = read_deployment_monitor()
    execution_summary = read_execution_summary()
    roadmap = read_roadmap()
    revenue = read_revenue_report()
    swarm = read_swarm_summary()
    cross_project = read_cross_project_summary()
    strategy = read_strategy_report()
    market = read_market_intelligence()
    priority = read_priority_report()
    experiments = read_experiment_summary()
    evolution = read_evolution_report()
    web_intel = read_web_intelligence()
    seo_opps = read_seo_opportunities()
    competitor_mem = read_competitor_memory()
    social_signals = read_social_signals()
    traffic_intel = read_traffic_intelligence()
    monetization = read_monetization_report()
    campaigns = read_campaign_report()
    realtime_alerts = read_realtime_alerts()
    knowledge_graph = read_knowledge_graph()
    growth = read_growth_report()
    monetization_runtime = read_monetization_runtime_report()
    conversion = read_conversion_report()
    acquisition = read_acquisition_report()
    scaling = read_scaling_report()
    deployment_pipeline = read_deployment_pipeline_report()
    vector_memory = read_vector_memory_stats()
    retrieval = read_retrieval_results()
    tool_runtime = read_tool_runtime_report()
    research = read_research_report()
    sandbox = read_sandbox_report()
    observability = read_observability_report()
    programmatic_seo = read_programmatic_seo_report()
    product_builder = read_product_builder_report()
    client_acquisition = read_client_acquisition_report()
    analytics_syncer = read_analytics_syncer_report()
    revenue_tracker = read_revenue_tracker_report()
    page_deployer = read_page_deployer_report()
    roi_agent = read_roi_prioritizer_report()
    kpi_tracker = read_kpi_report()
    agent_bus = read_agent_bus()
    cognition = read_cognition_report()
    governance = read_governance_report()
    runtime = read_runtime_report()
    task_economy = read_task_economy_report()
    agent_evolution = read_agent_evolution_report()
    kernel = read_kernel_report()
    game_factory = read_game_factory_report()
    game_seo = read_game_seo_report()
    game_qa = read_game_qa_report()
    admin_governance = read_admin_governance_report()
    telegram_logs = read_telegram_logs()
    indexing = read_indexing_report()
    publishing_pipeline = read_publishing_pipeline_report()
    game_assets = read_game_asset_report()
    print(f"[dashboard] {len(outputs)} outputs, {len(prs)} PRs, {len(automerge_log)} merge events, "
          f"{len(product_outputs)} product features, {visual_qa.get('total', 0)} QA reports, "
          f"{ai_qa.get('total', 0)} AI QA reviews, {roadmap.get('total_items', 0)} roadmap items, "
          f"{swarm.get('total_missions', 0)} swarm missions, "
          f"${revenue.get('portfolio_summary', {}).get('total_est_value_usd', 0):.2f} portfolio value")

    loops, active_loops = build_loops(outputs)
    ai_analytics = build_ai_analytics(outputs)

    by_project = {}
    for o in outputs:
        p = o.get("project", "unknown")
        by_project[p] = by_project.get(p, 0) + 1

    ai_outs = [o for o in outputs if o.get("ai_generated")]

    dashboard = {
        "generated_at": now_iso(),
        "architecture": "github-native",
        "scheduler": {
            "scheduler_running": True,
            "active_loops": active_loops,
            "total_loops": len(loops),
            "total_runs": sum(l["run_count"] for l in loops),
            "total_success": sum(l["success_count"] for l in loops),
            "loops": loops,
            "provider_cooldowns": {
                "openai": {"consecutive_429s": 0, "total_429s": 0, "last_success": now_iso()},
                "gemini": {"consecutive_429s": 0, "total_429s": 0, "last_success": now_iso()},
            },
        },
        "providers": {
            "openai": {"configured": True, "available": True},
            "gemini": {"configured": bool(os.environ.get("GEMINI_API_KEY")), "available": True},
            "github_active": True,
            "ai_mode": "ai" if ai_outs else "template",
            "market_data": {"twelve_data": False, "alpha_vantage": False},
        },
        "ai_analytics": ai_analytics,
        "outputs": {
            "total": len(outputs),
            "yallaplays": by_project.get("yallaplays", 0),
            "fionera": by_project.get("fionera", 0),
            "mifteh": by_project.get("mifteh", 0),
            "ai_generated": len(ai_outs),
            "template_generated": len(outputs) - len(ai_outs),
            "pending_review": len([o for o in outputs if o.get("pr_ready")]),
        },
        "repository": {
            "previews": [],
            "pr_outputs": [
                {
                    "output_id": o.get("suggested_branch", ""),
                    "project": o.get("project", ""),
                    "output_type": o.get("operation_type", ""),
                    "suggested_branch": o.get("suggested_branch", ""),
                    "generated_at": o.get("generated_at", ""),
                    "total_files": 2,
                }
                for o in outputs[:10] if o.get("pr_ready")
            ],
            "pr_ready": len([o for o in outputs if o.get("pr_ready")]),
        },
        "github_prs": [
            {
                "repo": p.get("repo", ""),
                "branch": p.get("branch", ""),
                "pr_number": p.get("pr_number"),
                "pr_url": p.get("pr_url", ""),
                "pr_title": p.get("pr_title", ""),
                "created_at": p.get("created_at", ""),
                "files_committed": p.get("files_committed", []),
            }
            for p in prs[-20:]
        ],
        "activity": [
            {
                "type": o.get("operation_type", "unknown"),
                "project": o.get("project", "unknown"),
                "title": o.get("title", "Untitled"),
                "ai_generated": o.get("ai_generated", False),
                "time": o.get("generated_at"),
            }
            for o in outputs[:50]
        ],
        "safety": {
            "auto_merge": False,
            "auto_deploy": False,
            "preview_first": True,
            "rollback_enabled": True,
            "validation_required": True,
            "audit_tracking": True,
        },
        "trust": {
            "repos": trust.get("repos", {}),
            "categories": trust.get("categories", {}),
            "suspended_repos": trust.get("suspended_repos", []),
            "suspended_categories": trust.get("suspended_categories", []),
            "last_updated": trust.get("generated_at", ""),
        },
        "apply_history": [
            {
                "repo": e.get("repo"),
                "pr_number": e.get("pr_number"),
                "pr_url": e.get("pr_url"),
                "action": e.get("action"),
                "score": e.get("score"),
                "reason": e.get("reason"),
                "evaluated_at": e.get("evaluated_at"),
                "merge_sha": e.get("merge_sha", ""),
            }
            for e in automerge_log[-50:]
        ],
        "product": product_metrics,
        "visual_qa": visual_qa,
        "self_improvement": self_improvement,
        "memory": memory_summary,
        "browser_qa": browser_qa,
        "ai_qa": ai_qa,
        "deployment_monitor": deployment_monitor,
        "executor": execution_summary,
        "roadmap": roadmap,
        "revenue": revenue,
        "swarm": swarm,
        "cross_project": cross_project,
        "strategy": strategy,
        "market": market,
        "priority": priority,
        "experiments": experiments,
        "evolution": evolution,
        "web_intel": web_intel,
        "seo_opportunities": seo_opps,
        "competitor_memory": competitor_mem,
        "social_signals": social_signals,
        "traffic_intel": traffic_intel,
        "monetization": monetization,
        "campaigns": campaigns,
        "realtime_alerts": realtime_alerts,
        "knowledge_graph": knowledge_graph,
        "growth": growth,
        "monetization_runtime": monetization_runtime,
        "conversion": conversion,
        "acquisition": acquisition,
        "scaling": scaling,
        "deployment_pipeline": deployment_pipeline,
        "vector_memory": vector_memory,
        "retrieval": retrieval,
        "tool_runtime": tool_runtime,
        "research": research,
        "sandbox": sandbox,
        "observability": observability,
        "programmatic_seo": programmatic_seo,
        "product_builder": product_builder,
        "client_acquisition": client_acquisition,
        "analytics_syncer": analytics_syncer,
        "revenue_tracker": revenue_tracker,
        "page_deployer": page_deployer,
        "roi_agent": roi_agent,
        "kpi_tracker": kpi_tracker,
        "agent_bus": agent_bus,
        "cognition": cognition,
        "governance": governance,
        "runtime": runtime,
        "task_economy": task_economy,
        "agent_evolution": agent_evolution,
        "kernel": kernel,
        "game_factory": game_factory,
        "game_seo": game_seo,
        "game_qa": game_qa,
        "admin_governance": admin_governance,
        "telegram_logs": telegram_logs,
        "indexing": indexing,
        "publishing_pipeline": publishing_pipeline,
        "game_assets": game_assets,
        "analytics_intelligence": {
            "generated_at": analytics_intel.get("generated_at", ""),
            "data_source": analytics_intel.get("data_source", ""),
            "cross_project": analytics_intel.get("cross_project", {}),
            "projects": {
                pk: {
                    "overview": pdata.get("overview", {}),
                    "scores": pdata.get("scores", {}),
                    "top_pages": pdata.get("top_pages", [])[:5],
                    "low_pages": pdata.get("low_pages", [])[:3],
                    "top_content": pdata.get("top_content", [])[:5],
                    "search_queries": pdata.get("search_queries", [])[:5],
                    "engagement": pdata.get("engagement", {}),
                    "conversions": pdata.get("conversions", {}),
                    "top_opportunity": pdata.get("top_opportunity", ""),
                }
                for pk, pdata in analytics_intel.get("projects", {}).items()
            },
            "recommendations": analytics_intel.get("recommendations", []),
            "alert_thresholds": analytics_intel.get("alert_thresholds", []),
            "autonomous_decisions": analytics_intel.get("autonomous_decisions", []),
            "execution_summary": analytics_intel.get("execution_summary", ""),
            "estimated_impact": analytics_intel.get("estimated_impact", {}),
        },
        "validation_history": [
            {
                "repo": e.get("repo"),
                "base_url": e.get("base_url"),
                "passed": e.get("passed"),
                "total": e.get("total"),
                "ok": e.get("ok"),
                "validated_at": e.get("validated_at"),
            }
            for e in validation_log[-50:]
        ],
    }

    out = Path("frontend/dashboard/data/dashboard.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False))
    print(f"[dashboard] Written — {active_loops}/{len(loops)} loops active, {len(outputs)} outputs, {len(prs)} PRs")
    return dashboard


if __name__ == "__main__":
    main()
