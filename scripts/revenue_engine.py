"""
MIFTEH OS — Revenue Engine
Estimates revenue impact of every generated feature before merge.
Tracks: RPM, CTR, conversion impact, SEO value, token ROI, portfolio profitability.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

# Revenue model constants — updated based on project monetization type
REVENUE_MODELS = {
    "yallaplays": {
        "monetization": "display_ads",
        "rpm_usd": 1.8,
        "avg_session_pages": 2.5,
        "monthly_baseline_visits": 15000,
        "ctr_baseline": 0.045,
        "cpc_baseline": 0.08,
    },
    "fionera": {
        "monetization": "saas_freemium",
        "rpm_usd": 0.0,
        "avg_session_pages": 4.2,
        "monthly_baseline_visits": 8000,
        "conversion_rate_free": 0.15,
        "conversion_rate_paid": 0.04,
        "arpu_usd": 9.99,
    },
    "mifteh": {
        "monetization": "portfolio_authority",
        "rpm_usd": 0.0,
        "avg_session_pages": 2.0,
        "monthly_baseline_visits": 3000,
        "lead_conversion_rate": 0.008,
        "avg_lead_value_usd": 1500,
    },
}

SEO_VALUE_PER_VISIT = 0.35


def estimate_feature_revenue(feature: dict, project: str) -> dict:
    model = REVENUE_MODELS.get(project, {})
    feature_type = feature.get("feature_type", "page")
    est_visits = feature.get("estimated_monthly_visits", 0)

    seo_value = round(est_visits * SEO_VALUE_PER_VISIT, 2)
    monetization = model.get("monetization", "unknown")
    direct_revenue = 0.0

    if monetization == "display_ads":
        pageviews = est_visits * model.get("avg_session_pages", 2.0)
        direct_revenue = round((pageviews / 1000) * model.get("rpm_usd", 1.8), 2)

    elif monetization == "saas_freemium":
        new_signups = est_visits * model.get("conversion_rate_free", 0.10)
        new_paid = new_signups * model.get("conversion_rate_paid", 0.04)
        direct_revenue = round(new_paid * model.get("arpu_usd", 9.99), 2)

    elif monetization == "portfolio_authority":
        direct_revenue = round(
            est_visits * model.get("lead_conversion_rate", 0.005)
            * model.get("avg_lead_value_usd", 1000),
            2,
        )

    cost_usd = feature.get("cost_usd", 0.0)
    total_value = seo_value + direct_revenue
    roi_ratio = round(total_value / max(cost_usd, 0.001), 1)

    return {
        "feature_id": feature.get("id", feature.get("label", "")),
        "project": project,
        "feature_type": feature_type,
        "est_monthly_visits": est_visits,
        "seo_value_usd": seo_value,
        "direct_revenue_usd": direct_revenue,
        "total_value_usd": round(total_value, 2),
        "token_cost_usd": round(cost_usd, 6),
        "roi_ratio": roi_ratio,
        "monetization_model": monetization,
    }


def build_project_revenue_summary(product_outputs: list, project: str) -> dict:
    proj_outputs = [o for o in product_outputs if o.get("project") == project]
    model = REVENUE_MODELS.get(project, {})

    features = [estimate_feature_revenue(o, project) for o in proj_outputs]

    total_seo_value = sum(f["seo_value_usd"] for f in features)
    total_direct = sum(f["direct_revenue_usd"] for f in features)
    total_token_cost = sum(f["token_cost_usd"] for f in features)
    total_est_visits = sum(f["est_monthly_visits"] for f in features)

    baseline = model.get("monthly_baseline_visits", 1)
    traffic_growth_pct = round((total_est_visits / max(baseline, 1)) * 100, 1)
    total_value = total_seo_value + total_direct

    features_sorted = sorted(features, key=lambda x: x["roi_ratio"], reverse=True)

    return {
        "project": project,
        "monetization_model": model.get("monetization", "unknown"),
        "total_features": len(features),
        "baseline_monthly_visits": baseline,
        "added_monthly_visits": total_est_visits,
        "traffic_growth_pct": traffic_growth_pct,
        "total_seo_value_usd": round(total_seo_value, 2),
        "total_direct_revenue_usd": round(total_direct, 2),
        "total_estimated_value_usd": round(total_value, 2),
        "total_token_cost_usd": round(total_token_cost, 6),
        "portfolio_roi": round(total_value / max(total_token_cost, 0.001), 1),
        "top_roi_features": features_sorted[:5],
        "all_features": features,
    }


def run_ai_revenue_analysis(project_summaries: list, analytics_intel: dict) -> dict:
    system = (
        "You are a revenue intelligence analyst for an AI-driven content company. "
        "Analyze the revenue data and provide actionable insights for maximizing ROI."
    )

    compact = [
        {k: v for k, v in s.items() if k != "all_features"}
        for s in project_summaries
    ]

    prompt = f"""Revenue data across all projects:
{json.dumps(compact, indent=2)}

Analytics cross-project summary:
{json.dumps(analytics_intel.get("cross_project", {}), indent=2)}

Respond with JSON:
{{
  "portfolio_monthly_value_usd": 0,
  "highest_roi_project": "project_name",
  "revenue_opportunities": [
    {{
      "project": "name",
      "opportunity": "description",
      "est_monthly_uplift_usd": 0,
      "effort": "low|medium|high",
      "priority": 1
    }}
  ],
  "token_efficiency_analysis": "text",
  "recommended_budget_allocation": {{
    "yallaplays": 0.5,
    "fionera": 0.3,
    "mifteh": 0.2
  }},
  "30d_revenue_forecast_usd": 0,
  "90d_revenue_forecast_usd": 0,
  "key_insight": "most important revenue insight",
  "risk_factors": ["risk 1"]
}}
Return ONLY valid JSON."""

    try:
        data, _, _, ok = generate_json(system, prompt, max_tokens=1200)
        if not ok or data is None:
            raise ValueError("generate_json returned no data")
        return data
    except Exception as e:
        total = sum(s.get("total_estimated_value_usd", 0) for s in project_summaries)
        best = max(project_summaries, key=lambda x: x.get("portfolio_roi", 0), default={})
        return {
            "portfolio_monthly_value_usd": total,
            "highest_roi_project": best.get("project", ""),
            "revenue_opportunities": [],
            "token_efficiency_analysis": "AI analysis unavailable",
            "recommended_budget_allocation": {
                "yallaplays": 0.5, "fionera": 0.3, "mifteh": 0.2,
            },
            "30d_revenue_forecast_usd": round(total, 2),
            "90d_revenue_forecast_usd": round(total * 3.2, 2),
            "key_insight": "Static estimation only — AI analysis failed",
            "risk_factors": [],
            "error": str(e),
        }


def main():
    print("[revenue] Starting revenue engine...")

    product_outputs = []
    for proj_dir in Path("outputs").iterdir():
        if not proj_dir.is_dir() or proj_dir.name.startswith("."):
            continue
        product_dir = proj_dir / "product"
        if not product_dir.exists():
            continue
        for f in product_dir.glob("*.json"):
            try:
                product_outputs.append(json.loads(f.read_text()))
            except Exception:
                pass

    analytics_intel = {}
    intel_file = Path("memory/analytics_intelligence.json")
    if intel_file.exists():
        try:
            analytics_intel = json.loads(intel_file.read_text())
        except Exception:
            pass

    project_summaries = []
    for project in ["yallaplays", "fionera", "mifteh"]:
        summary = build_project_revenue_summary(product_outputs, project)
        project_summaries.append(summary)
        print(
            f"  [{project}] {summary['total_features']} features | "
            f"~${summary['total_estimated_value_usd']}/mo value | "
            f"ROI {summary['portfolio_roi']}x"
        )

    ai_analysis = run_ai_revenue_analysis(project_summaries, analytics_intel)

    total_value = sum(s["total_estimated_value_usd"] for s in project_summaries)
    total_cost = sum(s["total_token_cost_usd"] for s in project_summaries)

    report = {
        "generated_at": now_iso(),
        "projects": {s["project"]: s for s in project_summaries},
        "ai_analysis": ai_analysis,
        "portfolio_summary": {
            "total_features": sum(s["total_features"] for s in project_summaries),
            "total_est_value_usd": round(total_value, 2),
            "total_token_cost_usd": round(total_cost, 6),
            "portfolio_roi": round(total_value / max(total_cost, 0.001), 1),
            "30d_forecast_usd": ai_analysis.get("30d_revenue_forecast_usd", round(total_value, 2)),
            "90d_forecast_usd": ai_analysis.get("90d_revenue_forecast_usd", round(total_value * 3.2, 2)),
        },
    }

    out = Path("memory/revenue_report.json")
    out.write_text(json.dumps(report, indent=2))
    print(f"[revenue] Portfolio value: ${total_value:.2f}/mo | ROI {report['portfolio_summary']['portfolio_roi']}x")
    print(f"[revenue] Report → {out}")
    return report


if __name__ == "__main__":
    main()
