"""
Executive AI Dashboard
Aggregates all growth and intelligence metrics into a unified CEO-level view.
Produces revenue metrics, SEO metrics, deployment metrics, indexing metrics,
AI recommendations, and growth forecasts.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from scripts.intelligence.registry import get_all_active_projects, get_project
from scripts.intelligence.report_store import load_latest, save_summary, save, REPORTS_ROOT

DASHBOARD_FILE = Path("data/executive_dashboard.json")
REPORT_TYPE = "executive"


# ──────────────────────────────────────────────────────────────────────────────
# Metric aggregation helpers
# ──────────────────────────────────────────────────────────────────────────────

def _load(report_type: str, project_id: str) -> dict:
    return load_latest(report_type, project_id) or {}


def _pct_change(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


def _trend_arrow(delta: Optional[float]) -> str:
    if delta is None:
        return "→"
    return "↑" if delta > 2 else "↓" if delta < -2 else "→"


# ──────────────────────────────────────────────────────────────────────────────
# Revenue metrics block
# ──────────────────────────────────────────────────────────────────────────────

def build_revenue_block(project_id: str) -> dict:
    rev = _load("revenue", project_id)
    prev_rev = {}

    scoring = rev.get("scoring", {})
    revenue_est = rev.get("revenue", {}).get("revenue_usd", {})
    adsense = rev.get("adsense", {})

    return {
        "monetization_score": scoring.get("monetization_score", 0),
        "monetization_status": scoring.get("status", "unknown"),
        "ad_coverage_pct": adsense.get("coverage_pct", 0),
        "estimated_monthly_revenue_usd": revenue_est.get("mid", 0),
        "revenue_range_usd": {
            "low": revenue_est.get("low", 0),
            "high": revenue_est.get("high", 0),
        },
        "ctr_estimate_pct": rev.get("ctr", {}).get("ctr_estimate", {}).get("mid", 0),
        "top_revenue_action": rev.get("suggestions", [{}])[0].get("action", "Run revenue analysis") if rev.get("suggestions") else "Run revenue analysis",
        "estimated_uplift_usd": rev.get("total_estimated_uplift_usd", 0),
        "publisher_id": adsense.get("publisher_id", ""),
        "data_age": rev.get("analyzed_at") or rev.get("generated_at"),
    }


# ──────────────────────────────────────────────────────────────────────────────
# SEO metrics block
# ──────────────────────────────────────────────────────────────────────────────

def build_seo_block(project_id: str) -> dict:
    seo = _load("seo", project_id)
    traffic = _load("traffic", project_id)
    live = _load("live", project_id)

    seo_score = seo.get("overall_seo_score", 0)
    serp_score = traffic.get("serp", {}).get("avg_serp_score", 0)
    indexing_ready = seo.get("indexing_ready", False)
    issues = seo.get("total_issues", 0)
    orphans = seo.get("orphan_count", 0)
    sitemap_count = live.get("sitemap", {}).get("url_count", 0)

    quick_wins = traffic.get("keyword_opportunities", {}).get("quick_wins", [])
    top_kw = quick_wins[0]["keyword"] if quick_wins else "N/A"

    return {
        "seo_score": seo_score,
        "serp_score": serp_score,
        "indexing_ready": indexing_ready,
        "total_issues": issues,
        "orphan_pages": orphans,
        "sitemap_urls": sitemap_count,
        "top_keyword_opportunity": top_kw,
        "quick_win_keywords": len(quick_wins),
        "seasonal_multiplier": traffic.get("trends", {}).get("traffic_multiplier", 1.0),
        "seasonal_opportunity": traffic.get("trends", {}).get("seasonal_trend", {}).get("opportunity", ""),
        "data_age": seo.get("analyzed_at") or seo.get("generated_at"),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Deployment / production health block
# ──────────────────────────────────────────────────────────────────────────────

def build_deployment_block(project_id: str) -> dict:
    live = _load("live", project_id)
    health = _load("health", project_id)

    return {
        "health_score": live.get("health_score", 0),
        "overall_ok": live.get("overall_ok", False),
        "http_status": live.get("http", {}).get("status", 0),
        "response_ms": live.get("http", {}).get("response_ms", 0),
        "routes_live": live.get("routes", {}).get("live", 0),
        "routes_total": live.get("routes", {}).get("total", 0),
        "robots_ok": live.get("robots", {}).get("ok", False),
        "sitemap_ok": live.get("sitemap", {}).get("ok", False),
        "composite_score": health.get("composite_score", 0),
        "status": health.get("status", "unknown"),
        "alert_count": health.get("alert_count", 0),
        "data_age": live.get("validated_at") or live.get("generated_at"),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Indexing metrics block
# ──────────────────────────────────────────────────────────────────────────────

def build_indexing_block(project_id: str) -> dict:
    idx = _load("indexing", project_id)

    return {
        "indexing_score": idx.get("indexing_score", 0),
        "indexing_status": idx.get("indexing_status", "unknown"),
        "sitemap_urls": idx.get("sitemap", {}).get("total_urls", 0),
        "sitemap_freshness_days": idx.get("sitemap", {}).get("freshness_days"),
        "stale_urls": idx.get("sitemap", {}).get("stale_count", 0),
        "orphan_count": idx.get("orphans", {}).get("orphan_count", 0),
        "indexability_pct": idx.get("indexability", {}).get("indexability_pct", 0),
        "noindex_pages": idx.get("indexability", {}).get("noindex_count", 0),
        "broken_pages": idx.get("indexability", {}).get("broken_count", 0),
        "top_recommendation": idx.get("recommendations", ["Run indexing analysis"])[0] if idx.get("recommendations") else "Run indexing analysis",
        "data_age": idx.get("analyzed_at") or idx.get("generated_at"),
    }


# ──────────────────────────────────────────────────────────────────────────────
# A/B Testing summary block
# ──────────────────────────────────────────────────────────────────────────────

def build_ab_block(project_id: str) -> dict:
    ab = _load("ab_tests", project_id)

    results = ab.get("results", {})
    winners = {k: v.get("current_winner", "inconclusive") for k, v in results.items() if not v.get("error")}
    best_test, best_uplift = ab.get("top_opportunity", ("none", 0))
    if isinstance(best_test, list):
        best_test, best_uplift = best_test[0], best_test[1]

    return {
        "tests_run": ab.get("tests_run", 0),
        "active_winners": sum(1 for w in winners.values() if w not in ("control", "inconclusive")),
        "best_test": best_test,
        "best_uplift_pct": best_uplift,
        "winners": winners,
        "data_age": ab.get("run_at") or ab.get("generated_at"),
    }


# ──────────────────────────────────────────────────────────────────────────────
# AI Recommendations engine
# ──────────────────────────────────────────────────────────────────────────────

def generate_ai_recommendations(project_id: str, blocks: dict) -> list[dict]:
    """Generate prioritized, specific AI recommendations from all data blocks."""
    recs = []
    rev = blocks.get("revenue", {})
    seo = blocks.get("seo", {})
    deploy = blocks.get("deployment", {})
    idx = blocks.get("indexing", {})
    ab = blocks.get("ab_testing", {})

    # Critical: Site down
    if not deploy.get("overall_ok"):
        recs.append({
            "priority": "critical",
            "category": "deployment",
            "action": "Site may be down or degraded — run live validation immediately",
            "impact": "all_revenue",
            "effort": "immediate",
        })

    # High: No AdSense / low coverage
    coverage = rev.get("ad_coverage_pct", 0)
    if coverage < 50:
        recs.append({
            "priority": "high",
            "category": "monetization",
            "action": f"Increase AdSense coverage from {coverage}% to 80%+ — add ads to all game pages",
            "impact": f"+${rev.get('estimated_uplift_usd', 0):.0f}/mo estimated",
            "effort": "1-2 days",
        })

    # High: Poor SEO score
    seo_score = seo.get("seo_score", 0)
    if seo_score < 60:
        recs.append({
            "priority": "high",
            "category": "seo",
            "action": f"Fix {seo.get('total_issues', 0)} SEO issues — current score {seo_score}/100",
            "impact": "+30-50% organic traffic within 60 days",
            "effort": "3-5 days",
        })

    # High: Not indexing ready
    if not seo.get("indexing_ready"):
        recs.append({
            "priority": "high",
            "category": "indexing",
            "action": "Site not ready for search indexing — fix canonical, noindex, and meta issues",
            "impact": "Critical for organic traffic",
            "effort": "1 day",
        })

    # Medium: Orphan pages
    orphans = idx.get("orphan_count", 0)
    if orphans > 0:
        recs.append({
            "priority": "medium",
            "category": "indexing",
            "action": f"Add internal links to {orphans} orphan pages — they won't rank without links",
            "impact": "+{orphans} pages eligible for ranking".format(orphans=orphans),
            "effort": "1-2 days",
        })

    # Medium: A/B winner ready to deploy
    best_uplift = ab.get("best_uplift_pct", 0)
    if best_uplift > 10:
        recs.append({
            "priority": "medium",
            "category": "ab_testing",
            "action": f"Deploy A/B winner '{ab.get('best_test')}' — {best_uplift:.0f}% improvement detected",
            "impact": f"+{best_uplift:.0f}% on {ab.get('best_test')} metric",
            "effort": "0.5 days",
        })

    # Medium: Keyword opportunity
    quick_wins = seo.get("quick_win_keywords", 0)
    top_kw = seo.get("top_keyword_opportunity", "")
    if quick_wins > 0:
        recs.append({
            "priority": "medium",
            "category": "content",
            "action": f"Create content for {quick_wins} low-difficulty keywords — start with: '{top_kw}'",
            "impact": "+{q} new ranking opportunities".format(q=quick_wins),
            "effort": "2-3 days",
        })

    # Low: Seasonal opportunity
    seasonal_mult = seo.get("seasonal_multiplier", 1.0)
    seasonal_opp = seo.get("seasonal_opportunity", "")
    if seasonal_mult >= 1.3 and seasonal_opp:
        recs.append({
            "priority": "low",
            "category": "traffic",
            "action": f"Capitalize on {seasonal_opp} — traffic {seasonal_mult}x baseline this period",
            "impact": f"Up to {int((seasonal_mult - 1) * 100)}% traffic boost",
            "effort": "1 day",
        })

    return sorted(recs, key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}[r["priority"]])


# ──────────────────────────────────────────────────────────────────────────────
# Growth forecasting
# ──────────────────────────────────────────────────────────────────────────────

def build_growth_forecast(blocks: dict, monthly_pageviews: int = 10000) -> dict:
    """Generate 3-month and 12-month revenue/traffic growth forecasts."""
    rev = blocks.get("revenue", {})
    seo = blocks.get("seo", {})

    current_rev = rev.get("estimated_monthly_revenue_usd", 0)
    seo_score = seo.get("seo_score", 50)
    coverage = rev.get("ad_coverage_pct", 0)

    # Scenario modelling
    def forecast_scenario(seo_improvement: float, coverage_improvement: float, months: int) -> float:
        new_coverage = min(100, coverage + coverage_improvement)
        new_seo = min(100, seo_score + seo_improvement)
        traffic_mult = (new_seo / max(seo_score, 1)) ** 0.5
        coverage_mult = new_coverage / max(coverage, 1)
        monthly = current_rev * traffic_mult * (coverage_mult ** 0.5)
        return round(monthly, 2)

    conservative_3m = forecast_scenario(5, 10, 3)
    realistic_3m    = forecast_scenario(12, 20, 3)
    optimistic_3m   = forecast_scenario(20, 35, 3)

    conservative_12m = forecast_scenario(15, 25, 12)
    realistic_12m    = forecast_scenario(30, 40, 12)
    optimistic_12m   = forecast_scenario(45, 60, 12)

    return {
        "current_monthly_usd": current_rev,
        "3_month_forecast": {
            "conservative": conservative_3m,
            "realistic": realistic_3m,
            "optimistic": optimistic_3m,
        },
        "12_month_forecast": {
            "conservative": conservative_12m,
            "realistic": realistic_12m,
            "optimistic": optimistic_12m,
        },
        "assumptions": {
            "conservative": "Minimal SEO improvement, small coverage increase",
            "realistic": "Consistent monthly optimization, steady content growth",
            "optimistic": "Full A/B winners deployed, aggressive content expansion",
        },
        "annual_cumulative_realistic": round(
            sum(
                current_rev * (1 + (realistic_12m / max(current_rev, 0.01) - 1) * m / 12)
                for m in range(1, 13)
            ), 2
        ),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Full dashboard builder
# ──────────────────────────────────────────────────────────────────────────────

def build_project_executive(project_id: str) -> dict:
    """Build executive dashboard for one project."""
    p = get_project(project_id)

    blocks = {
        "revenue": build_revenue_block(project_id),
        "seo": build_seo_block(project_id),
        "deployment": build_deployment_block(project_id),
        "indexing": build_indexing_block(project_id),
        "ab_testing": build_ab_block(project_id),
    }

    recommendations = generate_ai_recommendations(project_id, blocks)
    forecast = build_growth_forecast(blocks)

    return {
        "project_id": project_id,
        "name": p.get("name", project_id),
        "domain": p.get("domain", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": blocks,
        "ai_recommendations": recommendations,
        "growth_forecast": forecast,
        "executive_summary": {
            "health": blocks["deployment"].get("status", "unknown"),
            "monthly_revenue_est": blocks["revenue"].get("estimated_monthly_revenue_usd", 0),
            "seo_score": blocks["seo"].get("seo_score", 0),
            "critical_actions": sum(1 for r in recommendations if r["priority"] == "critical"),
            "high_actions": sum(1 for r in recommendations if r["priority"] == "high"),
        },
    }


def build_dashboard() -> dict:
    """Build the full multi-project executive dashboard."""
    projects = get_all_active_projects()
    project_dashboards = {}

    for p in projects:
        try:
            project_dashboards[p["id"]] = build_project_executive(p["id"])
        except Exception as e:
            project_dashboards[p["id"]] = {
                "project_id": p["id"], "error": str(e),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    total_rev = sum(
        d.get("metrics", {}).get("revenue", {}).get("estimated_monthly_revenue_usd", 0)
        for d in project_dashboards.values()
        if not d.get("error")
    )

    all_recs = [
        {**r, "project_id": pid}
        for pid, d in project_dashboards.items()
        for r in d.get("ai_recommendations", [])
        if not d.get("error")
    ]
    all_recs.sort(key=lambda r: {"critical": 0, "high": 1, "medium": 2, "low": 3}[r.get("priority", "low")])

    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "portfolio_summary": {
            "project_count": len(project_dashboards),
            "total_monthly_revenue_est_usd": round(total_rev, 2),
            "total_recommendations": len(all_recs),
            "critical_actions": sum(1 for r in all_recs if r.get("priority") == "critical"),
        },
        "top_recommendations": all_recs[:10],
        "projects": project_dashboards,
    }

    # Save to data/ for the web dashboard
    DASHBOARD_FILE.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_FILE.write_text(json.dumps(dashboard, indent=2, default=str))

    # Save as intelligence report
    save_summary(dashboard)
    for pid in project_dashboards:
        try:
            save(REPORT_TYPE, pid, project_dashboards[pid])
        except Exception:
            pass

    return dashboard


def print_executive_summary(dashboard: dict) -> None:
    portfolio = dashboard.get("portfolio_summary", {})
    print(f"\n{'═'*65}")
    print(f"  MIFTEH AI OS — Executive Dashboard")
    print(f"  {dashboard.get('generated_at', '')}")
    print(f"{'═'*65}")
    print(f"\n  Portfolio: {portfolio.get('project_count')} projects")
    print(f"  Est. Monthly Revenue: ${portfolio.get('total_monthly_revenue_est_usd', 0):.2f}")
    print(f"  Total AI Recommendations: {portfolio.get('total_recommendations', 0)}")
    print(f"  Critical Actions: {portfolio.get('critical_actions', 0)}")

    print(f"\n  {'─'*60}")
    print(f"  TOP AI RECOMMENDATIONS")
    print(f"  {'─'*60}")
    for i, rec in enumerate(dashboard.get("top_recommendations", [])[:5], 1):
        prio = rec.get("priority", "?").upper()
        cat = rec.get("category", "")
        action = rec.get("action", "")[:55]
        proj = rec.get("project_id", "")
        print(f"  {i}. [{prio:8}] [{cat}] {action}")
        print(f"     Project: {proj} | Impact: {rec.get('impact', 'N/A')}")

    print(f"\n  {'─'*60}")
    for pid, d in dashboard.get("projects", {}).items():
        if d.get("error"):
            print(f"  {pid}: ERROR — {d['error']}")
            continue
        summ = d.get("executive_summary", {})
        rev = summ.get("monthly_revenue_est", 0)
        seo = summ.get("seo_score", 0)
        health = summ.get("health", "?")
        critical = summ.get("critical_actions", 0)
        high = summ.get("high_actions", 0)
        print(f"  {pid:20} ${rev:6.2f}/mo  SEO:{seo:3}/100  {health.upper():10} C:{critical} H:{high}")

    print(f"\n{'═'*65}\n")


if __name__ == "__main__":
    d = build_dashboard()
    if "--json" in sys.argv:
        p_out = {k: v for k, v in d.items() if k != "projects"}
        print(json.dumps(p_out, indent=2, default=str))
    else:
        print_executive_summary(d)
