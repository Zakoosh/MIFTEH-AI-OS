"""
MIFTEH OS — Deployment Pipeline
Preview deployments, staging validation, production rollout health scoring,
automatic rollback triggers, deployment snapshots, Core Web Vitals tracking.
Integrates with GitHub Deployments API and PageSpeed Insights.
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_REPO = os.environ.get("GITHUB_REPOSITORY", "Zakoosh/MIFTEH-AI-OS")

PROJECTS = {
    "yallaplays": {
        "domain": "yallaplays.com",
        "github_repo": "Zakoosh/yallaplays",
        "branch": "main",
        "environments": ["preview", "staging", "production"],
        "health_thresholds": {"performance": 70, "accessibility": 80, "seo": 85},
    },
    "fionera": {
        "domain": "fionera.com",
        "github_repo": "Zakoosh/fionera",
        "branch": "main",
        "environments": ["preview", "staging", "production"],
        "health_thresholds": {"performance": 75, "accessibility": 85, "seo": 90},
    },
    "mifteh": {
        "domain": "mifteh.com",
        "github_repo": "Zakoosh/mifteh",
        "branch": "main",
        "environments": ["preview", "staging", "production"],
        "health_thresholds": {"performance": 80, "accessibility": 90, "seo": 95},
    },
}

ROLLBACK_TRIGGERS = {
    "performance_below": 50,
    "error_rate_above_pct": 5,
    "availability_below_pct": 99,
    "lcp_above_ms": 4000,
    "cls_above": 0.25,
}

CWV_THRESHOLDS = {
    "lcp_good_ms": 2500,
    "lcp_poor_ms": 4000,
    "fid_good_ms": 100,
    "fid_poor_ms": 300,
    "cls_good": 0.1,
    "cls_poor": 0.25,
    "ttfb_good_ms": 800,
    "ttfb_poor_ms": 1800,
}


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def fetch_pagespeed(url, strategy="mobile"):
    """Query PageSpeed Insights API (no key required for basic usage)."""
    api_url = (
        f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
        f"?url={urllib.request.quote(url)}&strategy={strategy}"
    )
    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "MIFTEH-AI-OS/1.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode())
        cats = data.get("lighthouseResult", {}).get("categories", {})
        audits = data.get("lighthouseResult", {}).get("audits", {})
        return {
            "performance": round((cats.get("performance", {}).get("score", 0) or 0) * 100),
            "accessibility": round((cats.get("accessibility", {}).get("score", 0) or 0) * 100),
            "seo": round((cats.get("seo", {}).get("score", 0) or 0) * 100),
            "best_practices": round((cats.get("best-practices", {}).get("score", 0) or 0) * 100),
            "lcp_ms": round((audits.get("largest-contentful-paint", {}).get("numericValue") or 0)),
            "cls": round((audits.get("cumulative-layout-shift", {}).get("numericValue") or 0), 3),
            "fid_ms": round((audits.get("max-potential-fid", {}).get("numericValue") or 0)),
            "ttfb_ms": round((audits.get("server-response-time", {}).get("numericValue") or 0)),
            "source": "pagespeed_insights",
            "strategy": strategy,
        }
    except Exception:
        return None


def check_url_availability(url):
    """Check if a URL is reachable and measure response time."""
    try:
        start = time.time()
        req = urllib.request.Request(
            f"https://{url}" if not url.startswith("http") else url,
            headers={"User-Agent": "MIFTEH-AI-OS/1.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            latency_ms = round((time.time() - start) * 1000)
            return {"available": True, "status_code": r.status, "latency_ms": latency_ms}
    except Exception as e:
        return {"available": False, "status_code": 0, "latency_ms": 0, "error": str(e)[:100]}


def fetch_github_deployments(repo):
    """Fetch recent GitHub deployments for a repo."""
    if not GITHUB_TOKEN:
        return []
    try:
        url = f"https://api.github.com/repos/{repo}/deployments?per_page=10"
        req = urllib.request.Request(
            url,
            headers={"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception:
        return []


def score_deployment_health(cwv, availability, thresholds):
    """Compute 0-100 deployment health score."""
    if not cwv and not availability.get("available"):
        return 0

    score = 100.0
    if cwv:
        if cwv.get("performance", 100) < thresholds["performance"]:
            score -= (thresholds["performance"] - cwv["performance"]) * 0.5
        if cwv.get("seo", 100) < thresholds["seo"]:
            score -= (thresholds["seo"] - cwv["seo"]) * 0.3
        lcp = cwv.get("lcp_ms", 0)
        if lcp > CWV_THRESHOLDS["lcp_poor_ms"]:
            score -= 20
        elif lcp > CWV_THRESHOLDS["lcp_good_ms"]:
            score -= 10
        cls = cwv.get("cls", 0)
        if cls > CWV_THRESHOLDS["cls_poor"]:
            score -= 15
        elif cls > CWV_THRESHOLDS["cls_good"]:
            score -= 7

    if not availability.get("available"):
        score -= 50
    elif availability.get("latency_ms", 0) > 3000:
        score -= 15

    return max(round(score), 0)


def detect_rollback_triggers(health_score, cwv, availability):
    """Return list of rollback trigger reasons if any threshold breached."""
    triggers = []
    if health_score < ROLLBACK_TRIGGERS["performance_below"]:
        triggers.append(f"Health score {health_score} < threshold {ROLLBACK_TRIGGERS['performance_below']}")
    if not availability.get("available"):
        triggers.append("Site unavailable")
    if cwv:
        if cwv.get("lcp_ms", 0) > ROLLBACK_TRIGGERS["lcp_above_ms"]:
            triggers.append(f"LCP {cwv['lcp_ms']}ms > {ROLLBACK_TRIGGERS['lcp_above_ms']}ms")
        if cwv.get("cls", 0) > ROLLBACK_TRIGGERS["cls_above"]:
            triggers.append(f"CLS {cwv['cls']} > {ROLLBACK_TRIGGERS['cls_above']}")
    return triggers


def create_deployment_snapshot(project_id, health_score, cwv, availability):
    """Save a timestamped deployment snapshot."""
    snapshots_dir = MEMORY_DIR / "deployment_snapshots"
    snapshots_dir.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    snap = {
        "project": project_id,
        "timestamp": now_iso(),
        "health_score": health_score,
        "cwv": cwv,
        "availability": availability,
    }
    snap_file = snapshots_dir / f"{project_id}_{ts}.json"
    snap_file.write_text(json.dumps(snap, indent=2))
    return str(snap_file.relative_to(MEMORY_DIR))


def ai_deployment_analysis(project_reports):
    """AI synthesizes deployment health across all projects."""
    system = (
        "You are a DevOps engineer specializing in web deployment health. "
        "Analyze deployment metrics and provide actionable recommendations. Return valid JSON only."
    )
    summary = {pid: {"health": p["health_score"], "available": p["availability"].get("available", False)}
               for pid, p in project_reports.items()}
    prompt = f"""Deployment health summary: {json.dumps(summary)}
Rollback triggers detected: {sum(len(p['rollback_triggers']) for p in project_reports.values())}

Return deployment analysis JSON:
{{
  "overall_deployment_health": 0-100,
  "deployment_status": "healthy|degraded|critical",
  "summary": "2-sentence deployment health overview",
  "critical_issues": ["issue1"],
  "recommendations": ["rec1", "rec2", "rec3"],
  "next_deployment_checklist": ["step1", "step2", "step3"]
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 400)
    if not ok:
        avg = round(sum(p["health_score"] for p in project_reports.values()) / max(len(project_reports), 1))
        data = {
            "overall_deployment_health": avg,
            "deployment_status": "healthy" if avg >= 70 else "degraded",
            "summary": f"Average deployment health {avg}/100 across {len(project_reports)} projects.",
            "critical_issues": [f"Rollback triggered for {pid}" for pid, p in project_reports.items() if p["rollback_triggers"]],
            "recommendations": ["Monitor Core Web Vitals daily", "Set up deployment health alerts", "Enable automatic rollback"],
            "next_deployment_checklist": ["Run Lighthouse CI", "Validate CWV thresholds", "Check availability probe"],
        }
    return data, tokens, cost


def main():
    print("[deployment_pipeline] Starting deployment health check...")

    all_tokens, all_cost = 0, 0.0
    project_reports = {}

    for project_id, config in PROJECTS.items():
        print(f"[deployment_pipeline] Checking {project_id} ({config['domain']})...")

        availability = check_url_availability(config["domain"])
        cwv = fetch_pagespeed(f"https://{config['domain']}", "mobile")
        if cwv is None:
            cwv = fetch_pagespeed(f"https://{config['domain']}", "desktop")

        health_score = score_deployment_health(cwv or {}, availability, config["health_thresholds"])
        rollback_triggers = detect_rollback_triggers(health_score, cwv or {}, availability)
        snapshot_path = create_deployment_snapshot(project_id, health_score, cwv, availability)

        gh_deployments = fetch_github_deployments(config["github_repo"])
        recent_deployment = gh_deployments[0] if gh_deployments else {}

        project_reports[project_id] = {
            "domain": config["domain"],
            "health_score": health_score,
            "health_status": "healthy" if health_score >= 70 else ("degraded" if health_score >= 40 else "critical"),
            "availability": availability,
            "cwv": cwv,
            "rollback_triggers": rollback_triggers,
            "rollback_recommended": len(rollback_triggers) > 0,
            "snapshot_path": snapshot_path,
            "recent_github_deployment": {
                "id": recent_deployment.get("id"),
                "environment": recent_deployment.get("environment"),
                "ref": recent_deployment.get("ref"),
                "created_at": recent_deployment.get("created_at"),
            } if recent_deployment else {},
        }

    analysis, tokens, cost = ai_deployment_analysis(project_reports)
    all_tokens += tokens
    all_cost += cost

    report = {
        "generated_at": now_iso(),
        "overall_health": analysis.get("overall_deployment_health", 0),
        "deployment_status": analysis.get("deployment_status", "unknown"),
        "projects": project_reports,
        "ai_analysis": analysis,
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "deployment_pipeline_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[deployment_pipeline] Done — overall health {report['overall_health']}/100, ${all_cost:.4f}")


if __name__ == "__main__":
    main()
