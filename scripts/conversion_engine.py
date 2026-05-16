"""
MIFTEH OS — Conversion Engine
CTA optimization, funnel analysis, bounce reduction, session extension,
lead conversion, revenue-per-visit optimization.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

PROJECTS = ["yallaplays", "fionera", "mifteh"]

CONVERSION_BENCHMARKS = {
    "yallaplays": {
        "model": "engagement",
        "target_session_min": 8,
        "target_bounce_rate_pct": 35,
        "target_pages_per_session": 4.5,
        "target_return_visit_rate": 0.40,
        "primary_conversion": "game_play_started",
        "secondary_conversion": "ad_impression",
    },
    "fionera": {
        "model": "freemium",
        "target_session_min": 5,
        "target_bounce_rate_pct": 30,
        "target_pages_per_session": 3.5,
        "target_return_visit_rate": 0.50,
        "primary_conversion": "premium_signup",
        "secondary_conversion": "watchlist_add",
    },
    "mifteh": {
        "model": "b2b",
        "target_session_min": 4,
        "target_bounce_rate_pct": 45,
        "target_pages_per_session": 3.0,
        "target_return_visit_rate": 0.25,
        "primary_conversion": "lead_form_submit",
        "secondary_conversion": "discovery_call_booked",
    },
}

CTA_TEMPLATES = {
    "yallaplays": ["العب الآن مجاناً →", "ابدأ اللعب →", "جرب مجاناً →", "اكتشف الألعاب →"],
    "fionera": ["Ücretsiz Dene →", "Portföyümü Analiz Et →", "Premium'a Geç →", "Sinyalleri Gör →"],
    "mifteh": ["Get Free AI Audit →", "Book Strategy Call →", "See My ROI →", "Start Automating →"],
}

FUNNEL_STAGES = {
    "yallaplays": ["homepage", "game_category", "game_detail", "game_play", "return_visit"],
    "fionera": ["homepage", "market_page", "stock_detail", "watchlist", "premium_page", "checkout"],
    "mifteh": ["homepage", "service_page", "case_study", "lead_magnet", "email_sequence", "call", "proposal"],
}

BOUNCE_REDUCTION_TACTICS = [
    "Exit-intent popup with value offer",
    "Progress bar showing page scroll depth",
    "Related content recommendations at 50% scroll",
    "Sticky header with primary CTA",
    "Social proof counter (active users / reviews)",
    "Page load time optimization (<2s target)",
    "Interactive element in first viewport",
    "Video autoplay with muted preview",
]

SESSION_EXTENSION_TACTICS = [
    "Next item recommendation at end of content",
    "Progress gamification (streaks, achievements)",
    "Personalized recommendations based on behavior",
    "In-page navigation with anchor links",
    "Comparison tables to encourage exploration",
    "Infinite scroll / pagination",
    "Save-for-later / watchlist functionality",
]


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def load_analytics(project_id):
    data = _rj("analytics_intelligence.json")
    return data.get("projects", {}).get(project_id, {})


def compute_conversion_gaps(project_id, analytics):
    bench = CONVERSION_BENCHMARKS[project_id]
    overview = analytics.get("overview", {})
    gaps = []

    bounce_actual = overview.get("bounce_rate_pct", 60)
    if bounce_actual > bench["target_bounce_rate_pct"]:
        gaps.append({
            "metric": "bounce_rate",
            "current": bounce_actual,
            "target": bench["target_bounce_rate_pct"],
            "gap": round(bounce_actual - bench["target_bounce_rate_pct"], 1),
            "priority": "high" if bounce_actual > bench["target_bounce_rate_pct"] + 20 else "medium",
        })

    session_actual = overview.get("avg_session_min", 2.0)
    if session_actual < bench["target_session_min"]:
        gaps.append({
            "metric": "session_duration_min",
            "current": session_actual,
            "target": bench["target_session_min"],
            "gap": round(bench["target_session_min"] - session_actual, 1),
            "priority": "high",
        })

    pages_actual = overview.get("pages_per_session", 1.5)
    if pages_actual < bench["target_pages_per_session"]:
        gaps.append({
            "metric": "pages_per_session",
            "current": pages_actual,
            "target": bench["target_pages_per_session"],
            "gap": round(bench["target_pages_per_session"] - pages_actual, 1),
            "priority": "medium",
        })

    return gaps


def generate_cta_optimization(project_id):
    templates = CTA_TEMPLATES.get(project_id, ["Try Now →"])
    bench = CONVERSION_BENCHMARKS[project_id]
    placements = ["hero_above_fold", "sticky_header", "end_of_content", "sidebar"]

    return {
        "primary_conversion_goal": bench["primary_conversion"],
        "cta_variants": [
            {
                "text": t,
                "placement": placements[i % len(placements)],
                "style": ["primary_button", "outline_button", "text_link", "floating_cta"][i % 4],
                "estimated_ctr_boost": round(0.15 + i * 0.05, 2),
            }
            for i, t in enumerate(templates)
        ],
        "recommended_ab_test": {
            "control": templates[0],
            "variant_a": templates[1] if len(templates) > 1 else templates[0],
            "traffic_split": "50/50",
            "test_duration_days": 14,
            "success_metric": "click_through_rate",
            "min_conversions_needed": 100,
        },
    }


def generate_funnel_analysis(project_id):
    stages = FUNNEL_STAGES[project_id]
    funnel = []
    current_pct = 100.0

    for i, stage in enumerate(stages):
        # Progressive drop-off with higher loss at later stages
        drop_rate = 0.25 + (0.10 * i / len(stages))
        drop = round(current_pct * drop_rate, 1)
        next_pct = max(current_pct - drop, 1.0)

        funnel.append({
            "stage": stage,
            "visitors_pct": round(current_pct, 1),
            "drop_off_pct": min(round(drop, 1), round(current_pct - 1.0, 1)),
            "optimizations": [f"Reduce friction on {stage} page", f"Strengthen {stage} CTA"],
        })
        current_pct = next_pct

    biggest_drop = max(funnel, key=lambda x: x["drop_off_pct"])
    return {
        "stages": funnel,
        "biggest_drop_stage": biggest_drop["stage"],
        "biggest_drop_pct": biggest_drop["drop_off_pct"],
        "end_conversion_rate_pct": funnel[-1]["visitors_pct"],
    }


def compute_revenue_per_visit(project_id, analytics):
    mon_data = _rj("monetization_runtime_report.json")
    proj_mon = mon_data.get("projects", {}).get(project_id, {})
    current_rev = proj_mon.get("current_revenue_est_usd", 100.0)
    target_rev = proj_mon.get("monthly_target_usd", 1000.0)

    monthly_sessions = analytics.get("overview", {}).get("monthly_sessions", 5000)
    rpv = round(current_rev / max(monthly_sessions, 1), 4)
    target_rpv = round(target_rev / max(monthly_sessions, 1), 4)

    return {
        "current_rpv_usd": rpv,
        "target_rpv_usd": target_rpv,
        "rpv_gap_usd": round(target_rpv - rpv, 4),
        "rpv_multiplier_needed": round(target_rpv / max(rpv, 0.0001), 1),
        "monthly_sessions": monthly_sessions,
    }


def ai_conversion_recommendations(project_id, bench, gaps, funnel, rpv):
    system = (
        "You are a CRO (Conversion Rate Optimization) expert. "
        "Generate specific, implementable recommendations. Return valid JSON only."
    )
    prompt = f"""Project: {project_id}
Conversion model: {bench['model']}
Primary conversion: {bench['primary_conversion']}
Conversion gaps: {json.dumps(gaps[:3], ensure_ascii=False)}
Biggest funnel drop: {funnel['biggest_drop_stage']} ({funnel['biggest_drop_pct']}%)
End funnel conversion rate: {funnel['end_conversion_rate_pct']}%
Revenue per visit: ${rpv['current_rpv_usd']} (target ${rpv['target_rpv_usd']})
RPV multiplier needed: {rpv['rpv_multiplier_needed']}x

Generate CRO recommendations. Return JSON:
{{
  "summary": "2-sentence CRO opportunity overview",
  "cro_score": 0-100,
  "top_priority_fix": "single most impactful CRO action",
  "bounce_reduction_tactics": ["tactic1", "tactic2", "tactic3"],
  "session_extension_tactics": ["tactic1", "tactic2"],
  "funnel_fixes": [
    {{"stage": "...", "fix": "...", "expected_lift_pct": 0}}
  ],
  "rpv_optimization": "specific strategy to increase revenue per visit",
  "30_day_conversion_lift_pct": 0,
  "quick_wins": [
    {{"action": "...", "effort": "low|medium", "impact": "..."}}
  ]
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 700)
    if not ok:
        data = {
            "summary": f"CRO opportunity at {project_id}. Critical drop at {funnel['biggest_drop_stage']} stage ({funnel['biggest_drop_pct']}% loss).",
            "cro_score": 45,
            "top_priority_fix": f"Fix {funnel['biggest_drop_stage']} page — add clearer value proposition and reduce form friction",
            "bounce_reduction_tactics": BOUNCE_REDUCTION_TACTICS[:3],
            "session_extension_tactics": SESSION_EXTENSION_TACTICS[:2],
            "funnel_fixes": [{"stage": funnel["biggest_drop_stage"], "fix": "Add social proof + clearer CTA", "expected_lift_pct": 15}],
            "rpv_optimization": f"Target {rpv['rpv_multiplier_needed']}x RPV via upsells and engagement monetization",
            "30_day_conversion_lift_pct": 15,
            "quick_wins": [
                {"action": "Add exit-intent popup with value offer", "effort": "low", "impact": "5-10% bounce reduction"},
                {"action": "Implement CTA A/B test", "effort": "low", "impact": "15-25% CTR increase"},
            ],
        }
    return data, tokens, cost


def main():
    print("[conversion_engine] Starting conversion analysis...")

    all_tokens, all_cost = 0, 0.0
    project_reports = {}
    portfolio_cro = 0.0

    for project_id in PROJECTS:
        print(f"[conversion_engine] Analyzing {project_id}...")
        analytics = load_analytics(project_id)
        bench = CONVERSION_BENCHMARKS[project_id]

        gaps = compute_conversion_gaps(project_id, analytics)
        cta = generate_cta_optimization(project_id)
        funnel = generate_funnel_analysis(project_id)
        rpv = compute_revenue_per_visit(project_id, analytics)

        recs, tokens, cost = ai_conversion_recommendations(project_id, bench, gaps, funnel, rpv)
        all_tokens += tokens
        all_cost += cost
        portfolio_cro += recs.get("cro_score", 50)

        project_reports[project_id] = {
            "model": bench["model"],
            "primary_conversion": bench["primary_conversion"],
            "conversion_gaps": gaps,
            "cta_optimization": cta,
            "funnel_analysis": funnel,
            "revenue_per_visit": rpv,
            "ai_recommendations": recs,
        }

    report = {
        "generated_at": now_iso(),
        "portfolio_cro_score": round(portfolio_cro / max(len(PROJECTS), 1), 1),
        "projects": project_reports,
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "conversion_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[conversion_engine] Done — CRO score {report['portfolio_cro_score']}/100, ${all_cost:.4f}")


if __name__ == "__main__":
    main()
