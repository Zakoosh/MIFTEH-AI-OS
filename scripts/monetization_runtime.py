"""
MIFTEH OS — Monetization Runtime
Executes monetization strategies per project: AdSense optimization,
sponsorship slots, affiliate blocks, premium features, lead funnels, pricing.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

MONETIZATION_CONFIGS = {
    "yallaplays": {
        "model": "ad-supported",
        "monthly_target_usd": 5000,
        "channels": {
            "adsense": {
                "enabled": True,
                "current_rpm": 0.80,
                "target_rpm": 2.50,
                "placements": ["header_leaderboard", "sidebar_300x250", "in-game_overlay", "footer_banner"],
                "ad_formats": ["display", "in-article", "auto"],
            },
            "game_sponsorship": {
                "enabled": True,
                "slots_available": 3,
                "price_per_slot_usd": 500,
                "cycle_days": 30,
                "categories": ["gaming_accessories", "mobile_games", "esports"],
            },
            "affiliate": {
                "enabled": True,
                "programs": [
                    {"name": "Amazon Gaming", "commission": 0.04},
                    {"name": "Razer Affiliate", "commission": 0.05},
                    {"name": "NordVPN Gaming", "commission": 0.40},
                ],
            },
            "engagement": {
                "enabled": True,
                "tactics": ["daily_login_rewards", "leaderboards", "achievements", "game_collections"],
                "target_session_duration_min": 8,
            },
        },
    },
    "fionera": {
        "model": "freemium",
        "monthly_target_usd": 8000,
        "channels": {
            "premium": {
                "enabled": True,
                "monthly_price_usd": 19.99,
                "annual_price_usd": 149.99,
                "target_conversion_rate": 0.03,
                "features": ["unlimited_watchlist", "ai_signals", "portfolio_analytics", "price_alerts", "export"],
            },
            "ai_signals": {
                "enabled": True,
                "types": ["buy_sell_signals", "trend_detection", "risk_alerts", "earnings_preview"],
                "accuracy_claim": "72% backtested accuracy",
            },
            "pro_dashboard": {
                "enabled": True,
                "price_usd": 49.99,
                "target_users": 200,
                "features": ["real_time_data", "custom_screener", "portfolio_tracking", "api_access"],
            },
        },
    },
    "mifteh": {
        "model": "b2b-services",
        "monthly_target_usd": 15000,
        "channels": {
            "lead_funnel": {
                "enabled": True,
                "lead_magnet": "Free AI Business Audit (Worth $500)",
                "target_leads_per_month": 50,
                "cta_placements": ["homepage_hero", "blog_sidebar", "exit_intent", "footer"],
            },
            "consulting": {
                "enabled": True,
                "hourly_rate_usd": 150,
                "retainer_monthly_usd": 3000,
                "discovery_call": "30-min free strategy call",
                "niches": ["AI automation", "AI integration", "AI strategy"],
            },
            "automation_packages": {
                "enabled": True,
                "tiers": [
                    {"name": "Starter", "price_usd": 2500, "deliverables": ["workflow_audit", "3_automations", "training"]},
                    {"name": "Growth", "price_usd": 7500, "deliverables": ["full_audit", "10_automations", "3mo_support", "reporting"]},
                    {"name": "Enterprise", "price_usd": 20000, "deliverables": ["full_transformation", "unlimited_automations", "dedicated_support", "custom_ai"]},
                ],
            },
        },
    },
}


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def compute_current_revenue_estimate(project_id, config, analytics):
    proj_analytics = analytics.get("projects", {}).get(project_id, {})
    monthly_sessions = proj_analytics.get("overview", {}).get("monthly_sessions", 5000)

    model = config["model"]
    if model == "ad-supported":
        rpm = config["channels"]["adsense"]["current_rpm"]
        return round(monthly_sessions / 1000 * rpm, 2)
    elif model == "freemium":
        users = monthly_sessions * 0.7
        rate = config["channels"]["premium"]["target_conversion_rate"]
        price = config["channels"]["premium"]["monthly_price_usd"]
        return round(users * rate * price, 2)
    elif model == "b2b-services":
        leads = config["channels"]["lead_funnel"]["target_leads_per_month"]
        avg_deal = config["channels"]["automation_packages"]["tiers"][0]["price_usd"]
        return round(leads * 0.10 * avg_deal, 2)
    return 0.0


def generate_adsense_optimization(config):
    ch = config["channels"]["adsense"]
    rpm_gap = ch["target_rpm"] - ch["current_rpm"]
    return {
        "current_rpm": ch["current_rpm"],
        "target_rpm": ch["target_rpm"],
        "rpm_gap": round(rpm_gap, 2),
        "revenue_uplift_at_target_pct": round(rpm_gap / ch["current_rpm"] * 100),
        "placement_recommendations": [
            {
                "placement": "in-game_overlay",
                "format": "interstitial",
                "est_rpm_boost": 0.40,
                "implementation": "Show after game-over screen with 5s skip",
            },
            {
                "placement": "header_leaderboard",
                "format": "responsive_display",
                "est_rpm_boost": 0.20,
                "implementation": "728x90 desktop / 320x50 mobile, lazy-load",
            },
            {
                "placement": "sidebar_300x250",
                "format": "display",
                "est_rpm_boost": 0.15,
                "implementation": "Sticky sidebar, auto-refresh every 60s",
            },
        ],
        "ad_density_note": "Max 2-3 ads per page (Google policy compliant)",
        "viewability_target_pct": 70,
        "affiliate_placements": [
            f"Gaming gear widget after game category pages",
            f"NordVPN banner for game download pages",
        ],
    }


def generate_premium_conversion_plan(config):
    ch = config["channels"]["premium"]
    annual_discount = round((1 - ch["annual_price_usd"] / (ch["monthly_price_usd"] * 12)) * 100)
    return {
        "monthly_price": ch["monthly_price_usd"],
        "annual_price": ch["annual_price_usd"],
        "annual_discount_pct": annual_discount,
        "target_conversion_rate": ch["target_conversion_rate"],
        "conversion_triggers": [
            "Hit 10 watchlist items → paywall prompt",
            "View 3rd AI signal in a session → upgrade overlay",
            "Export attempt → premium gate with preview",
            "Custom alert creation → premium gate",
        ],
        "onboarding_sequence": [
            "Day 0: Welcome email + 7-day free trial activation",
            "Day 3: Highlight most-used premium feature unlocked",
            "Day 6: Trial ends tomorrow + annual discount offer (save {annual_discount}%)",
            "Day 7: Downgrade confirmation + retention offer (30% off month 1)",
        ],
        "ai_signals_preview": {
            "free_tier": "3 signals/month",
            "premium_tier": "Unlimited signals",
            "hook": "Show blurred signal with 'Upgrade to see full analysis'",
        },
    }


def generate_lead_funnel(config):
    ch = config["channels"]["lead_funnel"]
    tiers = config["channels"]["automation_packages"]["tiers"]
    est_revenue = round(ch["target_leads_per_month"] * 0.10 * tiers[1]["price_usd"])
    return {
        "lead_magnet": ch["lead_magnet"],
        "landing_page_headline": "Get Your Free AI Business Audit — $500 Value, No Cost",
        "funnel_stages": [
            {"stage": "awareness", "channel": "SEO + content", "action": "Read AI automation guide"},
            {"stage": "interest", "channel": "Lead magnet", "action": "Download free AI audit checklist"},
            {"stage": "consideration", "channel": "Email sequence", "action": "Book 30-min strategy call"},
            {"stage": "decision", "channel": "Proposal", "action": "Review automation package"},
            {"stage": "close", "channel": "Direct", "action": "Sign contract + deposit"},
        ],
        "email_sequence_days": [1, 3, 5, 8, 12, 18, 25],
        "cta_variations": [
            "Get My Free AI Audit →",
            "Automate My Business Now →",
            "Book Free Strategy Call →",
            "See AI ROI Calculator →",
        ],
        "pricing_tiers": tiers,
        "target_leads_per_month": ch["target_leads_per_month"],
        "close_rate": 0.10,
        "estimated_monthly_revenue_usd": est_revenue,
    }


def compute_rpm_estimates(project_id, config, analytics):
    proj = analytics.get("projects", {}).get(project_id, {})
    monthly_sessions = proj.get("overview", {}).get("monthly_sessions", 5000)

    if config["model"] == "ad-supported":
        current_rpm = config["channels"]["adsense"]["current_rpm"]
        target_rpm = config["channels"]["adsense"]["target_rpm"]
        return {
            "current_rpm_usd": current_rpm,
            "target_rpm_usd": target_rpm,
            "monthly_sessions": monthly_sessions,
            "current_monthly_rev": round(monthly_sessions / 1000 * current_rpm, 2),
            "target_monthly_rev": round(monthly_sessions / 1000 * target_rpm, 2),
        }
    return {}


def ai_monetization_plan(project_id, config, current_revenue):
    system = (
        "You are an expert revenue optimization consultant. "
        "Generate specific, executable monetization plans. Return valid JSON only."
    )
    target = config["monthly_target_usd"]
    prompt = f"""Project: {project_id}
Monetization model: {config['model']}
Current estimated monthly revenue: ${current_revenue}
Monthly revenue target: ${target}
Revenue gap: ${round(target - current_revenue, 2)}
Active channels: {list(config['channels'].keys())}

Generate monetization execution plan. Return JSON:
{{
  "revenue_summary": "current state and opportunity in 2 sentences",
  "revenue_gap_strategy": "how to close the gap",
  "top_revenue_action": "single highest-impact action this week",
  "quick_revenue_wins": [
    {{"action": "...", "est_monthly_revenue_usd": 0, "timeline_days": 0, "effort": "low|medium|high"}}
  ],
  "pricing_optimization": "specific pricing recommendation",
  "conversion_rate_target": 0.0,
  "month_1_revenue_target_usd": 0.0,
  "month_3_revenue_target_usd": 0.0,
  "channel_priority": ["channel1", "channel2"]
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 600)
    if not ok:
        data = {
            "revenue_summary": f"{project_id} at ${current_revenue}/mo, targeting ${target}/mo.",
            "revenue_gap_strategy": f"Systematically activate all {config['model']} channels.",
            "top_revenue_action": "Optimize primary conversion funnel immediately",
            "quick_revenue_wins": [
                {"action": "Enable sticky ad units", "est_monthly_revenue_usd": 200, "timeline_days": 3, "effort": "low"},
            ],
            "pricing_optimization": "Test 20% price increase with annual discount bundle",
            "conversion_rate_target": 0.03,
            "month_1_revenue_target_usd": round(current_revenue * 1.3, 2),
            "month_3_revenue_target_usd": round(current_revenue * 2.0, 2),
            "channel_priority": list(config["channels"].keys())[:2],
        }
    return data, tokens, cost


def main():
    print("[monetization_runtime] Starting monetization analysis...")

    analytics = _rj("analytics_intelligence.json")

    all_tokens, all_cost = 0, 0.0
    project_reports = {}
    total_current = 0.0
    total_target = 0.0

    for project_id, config in MONETIZATION_CONFIGS.items():
        print(f"[monetization_runtime] Analyzing {project_id}...")

        current_revenue = compute_current_revenue_estimate(project_id, config, analytics)
        total_current += current_revenue
        total_target += config["monthly_target_usd"]

        implementations = {}
        rpm_data = {}
        if config["model"] == "ad-supported":
            implementations["adsense"] = generate_adsense_optimization(config)
            rpm_data = compute_rpm_estimates(project_id, config, analytics)
        elif config["model"] == "freemium":
            implementations["premium_conversion"] = generate_premium_conversion_plan(config)
        elif config["model"] == "b2b-services":
            implementations["lead_funnel"] = generate_lead_funnel(config)

        plan, tokens, cost = ai_monetization_plan(project_id, config, current_revenue)
        all_tokens += tokens
        all_cost += cost

        project_reports[project_id] = {
            "model": config["model"],
            "current_revenue_est_usd": current_revenue,
            "monthly_target_usd": config["monthly_target_usd"],
            "revenue_gap_usd": round(config["monthly_target_usd"] - current_revenue, 2),
            "rpm_estimates": rpm_data,
            "implementations": implementations,
            "ai_plan": plan,
        }

    report = {
        "generated_at": now_iso(),
        "portfolio_current_revenue_usd": round(total_current, 2),
        "portfolio_target_revenue_usd": total_target,
        "portfolio_revenue_gap_usd": round(total_target - total_current, 2),
        "projects": project_reports,
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "monetization_runtime_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[monetization_runtime] Done — ${total_current:.0f} current, ${total_target:.0f} target, ${all_cost:.4f}")


if __name__ == "__main__":
    main()
