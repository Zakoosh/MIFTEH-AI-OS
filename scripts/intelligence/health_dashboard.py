"""
Production Health Dashboard — aggregates live validation, SEO, and screenshot
reports into a unified multi-project health view.

Saves dashboard JSON to memory/reports/health/ and memory/reports/summary_latest.json.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .registry import get_all_active_projects, get_project
from .report_store import load_latest, save_summary, save, REPORTS_ROOT


# ──────────────────────────────────────────────────────────────────────────────
# Thresholds
# ──────────────────────────────────────────────────────────────────────────────

HEALTH_THRESHOLDS = {
    "critical": 40,
    "degraded": 65,
    "healthy": 80,
}

SEO_THRESHOLDS = {
    "poor": 40,
    "fair": 65,
    "good": 80,
}


def _status_label(score: int, thresholds: dict) -> str:
    if score >= thresholds.get("healthy", 80):
        return "healthy"
    if score >= thresholds.get("degraded", 65):
        return "degraded"
    return "critical"


# ──────────────────────────────────────────────────────────────────────────────
# Per-project health card
# ──────────────────────────────────────────────────────────────────────────────

def build_project_card(project_id: str) -> dict:
    """Build a health card for one project from latest reports."""
    p = get_project(project_id)

    live = load_latest("live", project_id) or {}
    seo = load_latest("seo", project_id) or {}
    screenshot = load_latest("screenshot", project_id) or {}
    pr_review = load_latest("pr_review", project_id) or {}

    # Live health
    live_score = live.get("health_score", 0)
    live_ok = live.get("overall_ok", False)
    live_at = live.get("validated_at") or live.get("generated_at")

    # HTTP availability
    http = live.get("http", {})
    http_status = http.get("status", 0)
    http_ok = http.get("ok", False)
    http_ms = http.get("response_ms", 0)

    # AdSense
    adsense = live.get("adsense", {})
    adsense_ok = adsense.get("ok")
    adsense_has_script = adsense.get("has_adsense_script", False)
    adsense_has_pub = adsense.get("has_publisher_id", False)

    # Routes
    routes = live.get("routes", {})
    routes_live = routes.get("live", 0)
    routes_total = routes.get("total", 0)
    routes_pct = int(routes_live / routes_total * 100) if routes_total else 0

    # Robots + Sitemap
    robots_ok = live.get("robots", {}).get("ok", False)
    sitemap_ok = live.get("sitemap", {}).get("ok", False)
    sitemap_count = live.get("sitemap", {}).get("url_count", 0)

    # SEO
    seo_score = seo.get("overall_seo_score", 0)
    seo_issues = seo.get("total_issues", 0)
    seo_indexing = seo.get("indexing_ready", False)
    seo_at = seo.get("analyzed_at") or seo.get("generated_at")

    # PR review
    pr_rec = pr_review.get("recommendation", "N/A")
    pr_risks_high = pr_review.get("risk_summary", {}).get("high", 0)
    pr_at = pr_review.get("reviewed_at") or pr_review.get("generated_at")

    # Screenshots
    ss_ok = screenshot.get("ok", None)
    ss_at = screenshot.get("captured_at") or screenshot.get("generated_at")

    # Composite score: weighted average
    component_scores = []
    if live_score:
        component_scores.append(("live", live_score, 0.40))
    if seo_score:
        component_scores.append(("seo", seo_score, 0.30))
    if routes_pct:
        component_scores.append(("routes", routes_pct, 0.20))
    adsense_score = 100 if adsense_ok else (50 if adsense_ok is None else 0)
    component_scores.append(("adsense", adsense_score, 0.10))

    if component_scores:
        total_weight = sum(w for _, _, w in component_scores)
        composite = int(sum(s * w for _, s, w in component_scores) / total_weight)
    else:
        composite = 0

    status = _status_label(composite, HEALTH_THRESHOLDS)

    # Alerts
    alerts = []
    if not http_ok:
        alerts.append({"severity": "critical", "message": f"Site unreachable (HTTP {http_status})"})
    if adsense_ok is False:
        alerts.append({"severity": "high", "message": "AdSense script missing or publisher ID not found"})
    if routes_pct < 80:
        alerts.append({"severity": "high", "message": f"Only {routes_live}/{routes_total} routes live"})
    if not robots_ok:
        alerts.append({"severity": "medium", "message": "robots.txt missing or misconfigured"})
    if not sitemap_ok:
        alerts.append({"severity": "medium", "message": "sitemap.xml missing or empty"})
    if seo_score < SEO_THRESHOLDS["poor"]:
        alerts.append({"severity": "high", "message": f"SEO score critical: {seo_score}/100"})
    elif seo_score < SEO_THRESHOLDS["fair"]:
        alerts.append({"severity": "medium", "message": f"SEO score low: {seo_score}/100"})
    if not seo_indexing and seo_score > 0:
        alerts.append({"severity": "high", "message": "Site not ready for indexing"})
    if pr_risks_high >= 2:
        alerts.append({"severity": "high", "message": f"PR has {pr_risks_high} high-severity risks"})
    if http_ms > 3000:
        alerts.append({"severity": "medium", "message": f"Slow homepage response: {http_ms}ms"})

    return {
        "project_id": project_id,
        "name": p.get("name", project_id),
        "domain": p.get("domain", ""),
        "framework": p.get("framework", "unknown"),
        "composite_score": composite,
        "status": status,
        "alerts": alerts,
        "alert_count": len(alerts),
        "metrics": {
            "http": {
                "ok": http_ok,
                "status_code": http_status,
                "response_ms": http_ms,
            },
            "routes": {
                "live": routes_live,
                "total": routes_total,
                "pct": routes_pct,
            },
            "adsense": {
                "ok": adsense_ok,
                "has_script": adsense_has_script,
                "has_publisher_id": adsense_has_pub,
            },
            "seo": {
                "score": seo_score,
                "issues": seo_issues,
                "indexing_ready": seo_indexing,
            },
            "robots": {"ok": robots_ok},
            "sitemap": {"ok": sitemap_ok, "url_count": sitemap_count},
            "pr_review": {
                "recommendation": pr_rec,
                "high_risks": pr_risks_high,
            },
            "screenshots": {"ok": ss_ok},
        },
        "last_checked": {
            "live": live_at,
            "seo": seo_at,
            "pr_review": pr_at,
            "screenshot": ss_at,
        },
    }


# ──────────────────────────────────────────────────────────────────────────────
# Full dashboard
# ──────────────────────────────────────────────────────────────────────────────

def build_dashboard() -> dict:
    """Build the full multi-project health dashboard."""
    projects = get_all_active_projects()
    cards = {}
    for p in projects:
        try:
            cards[p["id"]] = build_project_card(p["id"])
        except Exception as e:
            cards[p["id"]] = {
                "project_id": p["id"],
                "status": "error",
                "error": str(e),
                "composite_score": 0,
                "alerts": [],
            }

    # Summary stats
    scores = [c["composite_score"] for c in cards.values() if isinstance(c.get("composite_score"), int)]
    avg_score = int(sum(scores) / len(scores)) if scores else 0

    status_counts = {"healthy": 0, "degraded": 0, "critical": 0, "error": 0}
    for c in cards.values():
        s = c.get("status", "error")
        status_counts[s] = status_counts.get(s, 0) + 1

    all_alerts = []
    for pid, card in cards.items():
        for alert in card.get("alerts", []):
            all_alerts.append({**alert, "project_id": pid})

    critical_alerts = [a for a in all_alerts if a["severity"] == "critical"]
    high_alerts = [a for a in all_alerts if a["severity"] == "high"]

    overall_status = (
        "critical" if status_counts["critical"] > 0 or critical_alerts else
        "degraded" if status_counts["degraded"] > 0 or high_alerts else
        "healthy"
    )

    dashboard = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overall_status": overall_status,
        "average_score": avg_score,
        "project_count": len(cards),
        "status_counts": status_counts,
        "total_alerts": len(all_alerts),
        "critical_alerts": critical_alerts,
        "high_alerts": high_alerts,
        "projects": cards,
    }

    # Save both as summary and as health report for each project
    save_summary(dashboard)
    for pid in cards:
        try:
            save("health", pid, cards[pid])
        except Exception:
            pass

    return dashboard


def print_dashboard(dashboard: dict) -> None:
    """Pretty-print the dashboard to stdout."""
    now = dashboard.get("generated_at", "")
    status = dashboard.get("overall_status", "?").upper()
    avg = dashboard.get("average_score", 0)
    print(f"\n{'='*60}")
    print(f"  MIFTEH AI OS — Production Health Dashboard")
    print(f"  {now}  |  Status: {status}  |  Avg Score: {avg}/100")
    print(f"{'='*60}")

    for pid, card in dashboard.get("projects", {}).items():
        score = card.get("composite_score", 0)
        card_status = card.get("status", "?").upper()
        domain = card.get("domain", "")
        alert_count = card.get("alert_count", 0)
        bar = "█" * (score // 10) + "░" * (10 - score // 10)
        print(f"\n  [{card_status:8}] {pid:20} {bar} {score:3}/100  {domain}")
        for alert in card.get("alerts", [])[:3]:
            sev = alert["severity"].upper()
            print(f"             ⚠  [{sev}] {alert['message']}")
        if alert_count > 3:
            print(f"             ... +{alert_count - 3} more alerts")

    print(f"\n{'='*60}\n")


if __name__ == "__main__":
    d = build_dashboard()
    if "--json" in sys.argv:
        print(json.dumps({k: v for k, v in d.items() if k != "projects"}, indent=2))
    else:
        print_dashboard(d)
