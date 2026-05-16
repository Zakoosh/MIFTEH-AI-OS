"""
MIFTEH OS — Monetization Engine
Gap detection, ad/CTA optimization, revenue lift estimation, pricing intelligence.
Reads revenue, traffic, and competitor data to produce monetization recommendations.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

# Monetization models and benchmarks per project
MONETIZATION_CONFIG = {
    "yallaplays": {
        "model": "display_ads",
        "primary_metric": "rpm_usd",
        "benchmark_rpm": 1.80,
        "benchmark_ctr": 0.02,
        "ad_density_target": 3,        # ads per page
        "alt_channels": ["affiliate", "sponsored_content", "premium_pass"],
        "currency": "USD",
    },
    "fionera": {
        "model": "saas_freemium",
        "primary_metric": "mrr_usd",
        "benchmark_arpu": 9.99,
        "free_to_paid_rate": 0.04,      # industry avg 4%
        "churn_rate": 0.05,             # 5%/mo
        "alt_channels": ["data_api", "white_label", "premium_alerts"],
        "currency": "USD",
    },
    "mifteh": {
        "model": "portfolio_authority",
        "primary_metric": "leads",
        "avg_lead_value_usd": 1500,
        "lead_close_rate": 0.15,
        "alt_channels": ["consulting", "ai_tools_saas", "content_sponsorship"],
        "currency": "USD",
    },
}

# Industry RPM benchmarks by content type
RPM_BENCHMARKS = {
    "gaming":          {"low": 0.80, "avg": 1.80, "high": 3.50},
    "finance":         {"low": 3.00, "avg": 8.00, "high": 15.00},
    "tech":            {"low": 2.00, "avg": 5.00, "high": 12.00},
    "general":         {"low": 0.50, "avg": 1.20, "high": 2.50},
}

# CTA conversion benchmarks
CTA_BENCHMARKS = {
    "email_signup":    {"avg_cvr": 0.02, "value_per_lead": 5},
    "free_trial":      {"avg_cvr": 0.03, "value_per_lead": 25},
    "upgrade_prompt":  {"avg_cvr": 0.005, "value_per_lead": 120},
    "affiliate_click": {"avg_cvr": 0.01, "value_per_lead": 3},
}


def load_source(path: str) -> dict:
    f = Path(path)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def detect_monetization_gaps(project: str, config: dict, traffic_data: dict,
                              revenue_data: dict, competitor_data: dict) -> list:
    gaps = []
    model = config["model"]

    proj_traffic = traffic_data.get("projects", {}).get(project, {})
    our_visits = proj_traffic.get("our_est_monthly_visits", 0)
    ai_analysis = proj_traffic.get("ai_analysis", {})
    est_visits = ai_analysis.get("est_current_monthly_visits", our_visits)

    proj_revenue = revenue_data.get("projects", {}).get(project, {})

    if model == "display_ads":
        current_rpm = proj_revenue.get("rpm_usd", config["benchmark_rpm"] * 0.6)
        benchmark = config["benchmark_rpm"]
        if current_rpm < benchmark * 0.8:
            gaps.append({
                "gap_type": "low_rpm",
                "severity": "high",
                "current": current_rpm,
                "benchmark": benchmark,
                "lift_potential_usd": round((benchmark - current_rpm) * est_visits / 1000, 0),
                "action": "Optimize ad placements: add sticky footer + in-content units",
            })
        if config.get("ad_density_target", 3) > 0:
            # Check competitor ad density from competitor memory
            comp_profiles = competitor_data.get("projects", {}).get(project, {}).get("profiles", [])
            comp_ads = sum(1 for p in comp_profiles if p.get("monetization", {}).get("has_ads"))
            if comp_ads == 0:
                gaps.append({
                    "gap_type": "missing_ad_positions",
                    "severity": "medium",
                    "action": "Competitors may use alternative monetization — investigate premium/affiliate",
                })

    elif model == "saas_freemium":
        free_to_paid = config.get("free_to_paid_rate", 0.04)
        current_mrr = proj_revenue.get("mrr_usd", 0)
        if current_mrr < 500:
            gaps.append({
                "gap_type": "low_mrr",
                "severity": "critical",
                "current_mrr": current_mrr,
                "action": "Launch upgrade prompts at usage limits: portfolio >5 stocks, export feature, alerts",
            })
        gaps.append({
            "gap_type": "annual_plan_missing",
            "severity": "medium",
            "action": "Offer annual plan at 20% discount — reduces churn, improves cash flow",
        })

    elif model == "portfolio_authority":
        current_leads = proj_revenue.get("monthly_leads", 0)
        if current_leads < 3:
            gaps.append({
                "gap_type": "low_lead_volume",
                "severity": "high",
                "current_leads_mo": current_leads,
                "action": "Add case studies page, contact CTA on every post, newsletter capture",
            })
        gaps.append({
            "gap_type": "no_productized_offer",
            "severity": "medium",
            "action": "Bundle AI OS consulting into $500/mo retainer — lower barrier than custom project",
        })

    return gaps


def estimate_revenue_lift(project: str, config: dict, gaps: list,
                          est_monthly_visits: int) -> dict:
    total_lift = 0
    per_gap = []

    for gap in gaps:
        lift = gap.get("lift_potential_usd", 0)
        if not lift:
            # Estimate by gap type
            if gap["gap_type"] == "low_mrr":
                lift = 500  # conservative MRR gain
            elif gap["gap_type"] == "annual_plan_missing":
                lift = 200
            elif gap["gap_type"] == "low_lead_volume":
                lift = config.get("avg_lead_value_usd", 0) * config.get("lead_close_rate", 0.1)
            elif gap["gap_type"] == "no_productized_offer":
                lift = 1000
            elif gap["gap_type"] == "missing_ad_positions":
                lift = round(est_monthly_visits * 0.5 / 1000, 0)
        per_gap.append({**gap, "est_monthly_lift_usd": round(lift, 0)})
        total_lift += lift

    return {
        "total_est_monthly_lift_usd": round(total_lift, 0),
        "total_est_annual_lift_usd": round(total_lift * 12, 0),
        "gap_lifts": per_gap,
    }


def generate_monetization_plan(project: str, config: dict, gaps: list,
                                lift: dict, competitor_data: dict) -> dict:
    system = (
        "You are a monetization strategist. Generate specific, implementable revenue "
        "optimization plans with concrete actions and expected outcomes."
    )
    comp_patterns = competitor_data.get("projects", {}).get(project, {}).get("patterns", {})

    prompt = f"""Project: {project}
Monetization model: {config['model']}
Detected gaps: {json.dumps(gaps, indent=2)}
Revenue lift potential: {json.dumps(lift, indent=2)}
Competitor monetization patterns: {json.dumps(comp_patterns.get('monetization_patterns', [])[:3], indent=2)}

Generate monetization optimization plan. Respond with JSON:
{{
  "monetization_score": 0,
  "quick_wins": [
    {{"action": "description", "effort": "low|medium|high", "est_monthly_lift_usd": 0, "implement_in": "description"}}
  ],
  "cta_optimizations": [
    {{"placement": "header|hero|inline|footer|exit-intent", "cta_text": "text", "rationale": "why"}}
  ],
  "pricing_recommendation": {{
    "current_model": "description",
    "recommended_change": "description",
    "rationale": "why",
    "expected_impact": "description"
  }},
  "new_revenue_streams": [
    {{"stream": "description", "est_monthly_usd": 0, "implementation": "how"}}
  ],
  "30_day_action_plan": ["action 1", "action 2", "action 3"],
  "monetization_summary": "2 sentence monetization strategy"
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=1200)
    if ok and data:
        return data
    return {
        "monetization_score": 40,
        "quick_wins": [],
        "cta_optimizations": [],
        "pricing_recommendation": {},
        "new_revenue_streams": [],
        "30_day_action_plan": [],
        "monetization_summary": "Monetization plan generation failed — using conservative defaults.",
    }


def main():
    print("[monetization] Starting monetization engine...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    traffic_data   = load_source("memory/traffic_intelligence.json")
    revenue_data   = load_source("memory/revenue_report.json")
    competitor_data = load_source("memory/competitor_memory.json")

    all_projects = {}
    total_lift = 0

    for project, config in MONETIZATION_CONFIG.items():
        print(f"  [monetization] Analyzing {project}...")

        proj_traffic = traffic_data.get("projects", {}).get(project, {})
        est_visits = proj_traffic.get("ai_analysis", {}).get(
            "est_current_monthly_visits",
            proj_traffic.get("our_est_monthly_visits", 5000)
        )

        gaps = detect_monetization_gaps(project, config, traffic_data, revenue_data, competitor_data)
        lift = estimate_revenue_lift(project, config, gaps, est_visits)
        plan = generate_monetization_plan(project, config, gaps, lift, competitor_data)

        all_projects[project] = {
            "project": project,
            "model": config["model"],
            "analyzed_at": now_iso(),
            "gaps_detected": gaps,
            "revenue_lift": lift,
            "monetization_plan": plan,
        }

        mo_lift = lift["total_est_monthly_lift_usd"]
        total_lift += mo_lift
        print(f"    {len(gaps)} gaps | est. lift ${mo_lift:,.0f}/mo")

    report = {
        "generated_at": now_iso(),
        "projects": all_projects,
        "portfolio_monthly_lift_usd": round(total_lift, 0),
        "portfolio_annual_lift_usd": round(total_lift * 12, 0),
    }

    out = MEMORY_DIR / "monetization_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[monetization] Portfolio lift: ${total_lift:,.0f}/mo (${total_lift*12:,.0f}/yr)")
    print(f"[monetization] Report → {out}")
    return report


if __name__ == "__main__":
    main()
