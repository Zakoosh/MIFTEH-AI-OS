"""
MIFTEH OS — Revenue Tracker
Tracks real revenue metrics: RPM, CTR, AdSense earnings, Stripe MRR,
affiliate clicks, subscriptions, lead values, and conversion economics.
Computes profitability score per project and optimization recommendations.
Profitability-first: always optimizes toward highest-margin actions.
"""
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
HISTORY_FILE = MEMORY_DIR / "revenue_history.json"

REVENUE_TARGETS = {
    "yallaplays": {
        "model": "ad_supported",
        "monthly_target_usd": 5000,
        "rpm_target": 2.50,
        "ctr_target": 0.05,
        "traffic_target_sessions": 80000,
        "growth_rate_target": 0.15,
    },
    "fionera": {
        "model": "freemium_saas",
        "monthly_target_usd": 8000,
        "free_users_target": 5000,
        "paid_users_target": 200,
        "arpu_target_usd": 14.99,
        "trial_conversion_target": 0.08,
    },
    "mifteh": {
        "model": "b2b_services",
        "monthly_target_usd": 15000,
        "leads_target": 30,
        "clients_target": 5,
        "avg_deal_usd": 2499,
        "close_rate_target": 0.20,
    },
}

AFFILIATE_PROGRAMS = {
    "yallaplays": ["gaming_gear", "esports_platforms", "game_subscriptions"],
    "fionera": ["broker_referrals", "fintech_tools", "investing_courses"],
    "mifteh": ["ai_tools", "saas_tools", "hosting"],
}


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def load_revenue_history():
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass
    return {"snapshots": [], "created_at": now_iso()}


def compute_yallaplays_revenue(analytics, adsense_data):
    """Compute YallaPlays ad-supported revenue metrics."""
    baseline = analytics.get("project_analytics", {}).get("yallaplays", {}).get("baseline", {})
    cf_data = analytics.get("project_analytics", {}).get("yallaplays", {}).get("cloudflare", {})

    pageviews = cf_data.get("total_pageviews", baseline.get("pageviews", 15000))
    sessions = baseline.get("sessions", pageviews // 2)

    # AdSense real data if available
    if adsense_data.get("page_rpm"):
        rpm = adsense_data["page_rpm"]
        ctr = adsense_data.get("page_ctr", 0.04)
        earnings = adsense_data.get("estimated_earnings_usd", 0.0)
        data_source = "adsense_real"
    else:
        rpm = 1.85
        ctr = 0.042
        earnings = (pageviews / 1000) * rpm
        data_source = "estimated"

    target = REVENUE_TARGETS["yallaplays"]
    return {
        "model": "ad_supported",
        "data_source": data_source,
        "monthly_pageviews": pageviews,
        "monthly_sessions": sessions,
        "rpm_usd": round(rpm, 2),
        "ctr": round(ctr, 4),
        "estimated_monthly_earnings_usd": round(earnings, 2),
        "target_monthly_usd": target["monthly_target_usd"],
        "target_gap_usd": round(target["monthly_target_usd"] - earnings, 2),
        "rpm_vs_target": round(rpm / target["rpm_target"] * 100, 1),
        "traffic_vs_target": round(sessions / target["traffic_target_sessions"] * 100, 1),
        "affiliate_opportunities": AFFILIATE_PROGRAMS["yallaplays"],
        "profitability_score": round(min(100, (earnings / target["monthly_target_usd"]) * 100), 1),
    }


def compute_fionera_revenue(analytics, stripe_data):
    """Compute Fionera freemium SaaS revenue metrics."""
    baseline = analytics.get("project_analytics", {}).get("fionera", {}).get("baseline", {})
    sessions = baseline.get("sessions", 8000)

    # Stripe real data if available
    if stripe_data.get("total_revenue_usd"):
        mrr = stripe_data["total_revenue_usd"]
        paid_users = max(1, stripe_data.get("successful_charges", 1))
        arpu = stripe_data.get("avg_charge_usd", 14.99)
        data_source = "stripe_real"
    else:
        free_users = round(sessions * 0.4)
        paid_users = round(free_users * 0.04)
        arpu = 14.99
        mrr = paid_users * arpu
        data_source = "estimated"

    free_users = round(sessions * 0.4) if data_source == "estimated" else paid_users * 20
    target = REVENUE_TARGETS["fionera"]
    trial_cvr = paid_users / max(free_users, 1)

    return {
        "model": "freemium_saas",
        "data_source": data_source,
        "free_users_estimate": free_users,
        "paid_users": paid_users,
        "arpu_usd": round(arpu, 2),
        "mrr_usd": round(mrr, 2),
        "arr_usd": round(mrr * 12, 2),
        "trial_conversion_rate": round(trial_cvr, 4),
        "target_mrr_usd": target["monthly_target_usd"],
        "target_gap_usd": round(target["monthly_target_usd"] - mrr, 2),
        "paid_vs_target": round(paid_users / target["paid_users_target"] * 100, 1),
        "affiliate_programs": AFFILIATE_PROGRAMS["fionera"],
        "profitability_score": round(min(100, (mrr / target["monthly_target_usd"]) * 100), 1),
    }


def compute_mifteh_revenue(analytics, acquisition_report):
    """Compute Mifteh B2B services revenue metrics."""
    baseline = analytics.get("project_analytics", {}).get("mifteh", {}).get("baseline", {})
    sessions = baseline.get("sessions", 3000)

    leads_generated = acquisition_report.get("estimated_monthly_leads", 0)
    close_rate = 0.15
    clients = max(1, round(leads_generated * close_rate))
    avg_deal = REVENUE_TARGETS["mifteh"]["avg_deal_usd"]
    mrr = clients * avg_deal
    pipeline_value = leads_generated * avg_deal * 0.3

    target = REVENUE_TARGETS["mifteh"]
    return {
        "model": "b2b_services",
        "data_source": "estimated",
        "monthly_sessions": sessions,
        "leads_per_month": leads_generated,
        "estimated_clients": clients,
        "close_rate": close_rate,
        "avg_deal_usd": avg_deal,
        "estimated_mrr_usd": round(mrr, 2),
        "pipeline_value_usd": round(pipeline_value, 2),
        "target_mrr_usd": target["monthly_target_usd"],
        "target_gap_usd": round(target["monthly_target_usd"] - mrr, 2),
        "leads_vs_target": round(leads_generated / target["leads_target"] * 100, 1),
        "affiliate_programs": AFFILIATE_PROGRAMS["mifteh"],
        "profitability_score": round(min(100, (mrr / target["monthly_target_usd"]) * 100), 1),
    }


def compute_portfolio_totals(yp_rev, fio_rev, mif_rev):
    """Compute cross-portfolio revenue totals."""
    total_mrr = yp_rev["estimated_monthly_earnings_usd"] + fio_rev["mrr_usd"] + mif_rev["estimated_mrr_usd"]
    total_target = sum(t["monthly_target_usd"] for t in REVENUE_TARGETS.values())
    total_pipeline = mif_rev["pipeline_value_usd"]

    return {
        "total_mrr_usd": round(total_mrr, 2),
        "total_arr_usd": round(total_mrr * 12, 2),
        "total_target_usd": total_target,
        "target_attainment_pct": round(total_mrr / total_target * 100, 1),
        "total_pipeline_usd": round(total_pipeline, 2),
        "portfolio_profitability_score": round((yp_rev["profitability_score"] + fio_rev["profitability_score"] + mif_rev["profitability_score"]) / 3, 1),
        "highest_revenue_project": max(
            [("yallaplays", yp_rev["estimated_monthly_earnings_usd"]),
             ("fionera", fio_rev["mrr_usd"]),
             ("mifteh", mif_rev["estimated_mrr_usd"])],
            key=lambda x: x[1]
        )[0],
    }


def ai_revenue_optimization(yp_rev, fio_rev, mif_rev, totals):
    """AI generates profitability-first optimization recommendations."""
    system = (
        "You are a revenue optimization expert for a multi-project AI business. "
        "Prioritize profitability above all else. Return valid JSON only."
    )
    prompt = f"""Revenue snapshot:
YallaPlays (ads): ${yp_rev['estimated_monthly_earnings_usd']:.0f}/mo, RPM ${yp_rev['rpm_usd']}, target ${yp_rev['target_monthly_usd']:,}
Fionera (SaaS): ${fio_rev['mrr_usd']:.0f}/mo MRR, {fio_rev['paid_users']} paid users, target ${fio_rev['target_mrr_usd']:,}
Mifteh (B2B): ${mif_rev['estimated_mrr_usd']:.0f}/mo, {mif_rev['leads_per_month']} leads, target ${mif_rev['target_mrr_usd']:,}
Portfolio total: ${totals['total_mrr_usd']:.0f}/mo ({totals['target_attainment_pct']:.1f}% of target)

Return profitability-first analysis:
{{
  "revenue_score": 0-100,
  "attainment_status": "on_track|behind|ahead",
  "critical_revenue_actions": [
    {{"project": "name", "action": "specific action", "revenue_impact_usd": 0, "priority": "immediate|this_week|this_month"}}
  ],
  "rpm_optimization": {{"target_rpm": 2.50, "current_rpm": {yp_rev['rpm_usd']}, "tactics": ["tactic1"]}},
  "conversion_opportunities": ["opp1", "opp2"],
  "highest_roi_action": "single most impactful action",
  "profitability_ranking": ["yallaplays|fionera|mifteh ordered by profitability"],
  "executive_summary": "2-sentence revenue briefing"
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 500)
    if not ok:
        data = {
            "revenue_score": round(totals["target_attainment_pct"]),
            "attainment_status": "on_track" if totals["target_attainment_pct"] > 60 else "behind",
            "critical_revenue_actions": [
                {"project": "yallaplays", "action": "Increase pageviews to boost AdSense RPM", "revenue_impact_usd": 500, "priority": "this_week"},
                {"project": "fionera", "action": "Launch premium tier email campaign", "revenue_impact_usd": 1200, "priority": "this_week"},
                {"project": "mifteh", "action": "Activate consultation funnel lead magnets", "revenue_impact_usd": 2499, "priority": "immediate"},
            ],
            "rpm_optimization": {"target_rpm": 2.50, "current_rpm": yp_rev["rpm_usd"], "tactics": ["Add premium ad units", "Improve page load speed", "Target high-CPC keywords"]},
            "conversion_opportunities": ["Fionera: Add annual plan 20% discount", "Mifteh: Add ROI calculator lead magnet"],
            "highest_roi_action": "Mifteh consultation funnel activation — $2,499 avg deal, 48h close cycle",
            "profitability_ranking": ["mifteh", "fionera", "yallaplays"],
            "executive_summary": f"Portfolio at ${totals['total_mrr_usd']:.0f}/mo ({totals['target_attainment_pct']:.1f}% of ${totals['total_target_usd']:,} target). Mifteh B2B clients are the highest-margin path to target attainment.",
        }
    return data, tokens, cost


def update_revenue_history(history, snapshot):
    """Append current snapshot to rolling history."""
    history.setdefault("snapshots", [])
    history["snapshots"].append(snapshot)
    # Keep last 90 snapshots
    history["snapshots"] = history["snapshots"][-90:]
    history["updated_at"] = now_iso()
    return history


def main():
    print("[revenue_tracker] Starting revenue tracking cycle...")
    all_tokens, all_cost = 0, 0.0

    analytics = _rj("analytics_syncer_report.json")
    adsense_data = analytics.get("adsense", {})
    stripe_data = analytics.get("stripe", {})
    acquisition_report = _rj("client_acquisition_report.json")

    yp_rev = compute_yallaplays_revenue(analytics, adsense_data)
    print(f"[revenue_tracker] YallaPlays: ${yp_rev['estimated_monthly_earnings_usd']:.2f}/mo (RPM ${yp_rev['rpm_usd']})")

    fio_rev = compute_fionera_revenue(analytics, stripe_data)
    print(f"[revenue_tracker] Fionera: ${fio_rev['mrr_usd']:.2f}/mo MRR ({fio_rev['paid_users']} paid)")

    mif_rev = compute_mifteh_revenue(analytics, acquisition_report)
    print(f"[revenue_tracker] Mifteh: ${mif_rev['estimated_mrr_usd']:.2f}/mo ({mif_rev['leads_per_month']} leads)")

    totals = compute_portfolio_totals(yp_rev, fio_rev, mif_rev)
    print(f"[revenue_tracker] Portfolio total: ${totals['total_mrr_usd']:.2f}/mo ({totals['target_attainment_pct']:.1f}% target)")

    analysis, tokens, cost = ai_revenue_optimization(yp_rev, fio_rev, mif_rev, totals)
    all_tokens += tokens
    all_cost += cost

    snapshot = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "total_mrr_usd": totals["total_mrr_usd"],
        "yallaplays_usd": yp_rev["estimated_monthly_earnings_usd"],
        "fionera_usd": fio_rev["mrr_usd"],
        "mifteh_usd": mif_rev["estimated_mrr_usd"],
        "target_attainment_pct": totals["target_attainment_pct"],
    }

    history = load_revenue_history()
    history = update_revenue_history(history, snapshot)
    HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False))

    report = {
        "generated_at": now_iso(),
        "portfolio": totals,
        "projects": {
            "yallaplays": yp_rev,
            "fionera": fio_rev,
            "mifteh": mif_rev,
        },
        "revenue_score": analysis.get("revenue_score", 0),
        "attainment_status": analysis.get("attainment_status", "unknown"),
        "critical_revenue_actions": analysis.get("critical_revenue_actions", []),
        "rpm_optimization": analysis.get("rpm_optimization", {}),
        "conversion_opportunities": analysis.get("conversion_opportunities", []),
        "highest_roi_action": analysis.get("highest_roi_action", ""),
        "profitability_ranking": analysis.get("profitability_ranking", []),
        "executive_summary": analysis.get("executive_summary", ""),
        "recent_history": history["snapshots"][-7:],
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "revenue_tracker_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[revenue_tracker] Done — score {report['revenue_score']}/100, ${totals['total_mrr_usd']:.2f}/mo total, ${all_cost:.4f}")


if __name__ == "__main__":
    main()
