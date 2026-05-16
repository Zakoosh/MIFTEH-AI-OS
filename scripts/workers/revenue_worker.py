"""Revenue worker — reads revenue reports, tracks MRR/RPM, computes health."""
import json
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
KPI_REPORT = Path("memory/kpi_report.json")
REVENUE_REPORT = Path("memory/revenue_report.json")
PIPELINE_REPORT = Path("memory/publishing_pipeline_report.json")
OUTPUT_FILE = SNAPSHOT_DIR / "revenue_snapshot.json"

MRR_TARGET_USD = 500
RPM_MIN_USD = 0.80


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    kpi = _load_json(KPI_REPORT)
    revenue = _load_json(REVENUE_REPORT)
    pipeline = _load_json(PIPELINE_REPORT)

    issues = []
    opportunities = []

    # Extract MRR
    mrr = (
        revenue.get("mrr_usd", 0)
        or kpi.get("revenue", {}).get("mrr_usd", 0)
        or 0
    )

    # Extract RPM estimate from pipeline
    monetization = pipeline.get("monetization", {})
    avg_rpm = monetization.get("avg_rpm_usd", 0) or 0

    # Extract deployed game count
    deployed_games = pipeline.get("deployed_count", 0) or 0

    # Revenue health checks
    if mrr == 0:
        issues.append({
            "type": "no_mrr",
            "severity": "info",
            "detail": "MRR is $0 — monetization not yet active",
        })
    elif mrr < MRR_TARGET_USD * 0.1:
        issues.append({
            "type": "low_mrr",
            "severity": "warning",
            "detail": f"MRR ${mrr:.2f} is very low (target ${MRR_TARGET_USD})",
        })

    if avg_rpm > 0 and avg_rpm < RPM_MIN_USD:
        issues.append({
            "type": "low_rpm",
            "severity": "warning",
            "detail": f"Average RPM ${avg_rpm:.2f} below minimum ${RPM_MIN_USD}",
        })

    # Opportunities
    if deployed_games > 0 and mrr == 0:
        opportunities.append({
            "type": "adsense_setup",
            "detail": f"{deployed_games} games deployed — set up AdSense to start monetizing",
        })

    if deployed_games < 10:
        opportunities.append({
            "type": "scale_games",
            "detail": f"Only {deployed_games} games deployed — scale to 25+ for significant revenue",
        })

    health = "healthy"
    if any(i["severity"] == "warning" for i in issues):
        health = "warning"

    snapshot = {
        "worker": "revenue_worker",
        "timestamp": _now(),
        "status": "ok",
        "mrr_usd": mrr,
        "mrr_target_usd": MRR_TARGET_USD,
        "avg_rpm_usd": avg_rpm,
        "deployed_games": deployed_games,
        "issues": issues,
        "opportunities": opportunities,
        "health": health,
        "revenue_stage": "pre-revenue" if mrr == 0 else ("early" if mrr < 100 else "growing"),
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[revenue_worker] done — MRR=${mrr:.2f} health={health}")
    return snapshot


if __name__ == "__main__":
    run()
