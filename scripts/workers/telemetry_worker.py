"""Telemetry worker — aggregates all snapshots, computes system health state."""
import json
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
OUTPUT_FILE = SNAPSHOT_DIR / "telemetry_snapshot.json"
SYSTEM_HEALTH_FILE = Path("memory/system_health.json")

WORKER_SNAPSHOTS = [
    "analytics_snapshot.json",
    "indexing_snapshot.json",
    "seo_snapshot.json",
    "github_snapshot.json",
    "revenue_snapshot.json",
    "publishing_snapshot.json",
    "games_snapshot.json",
]

# Health state precedence (worst wins)
HEALTH_RANK = {"healthy": 0, "info": 1, "warning": 2, "degraded": 3, "critical": 4, "unknown": 1}
HEALTH_STATES = ["healthy", "warning", "degraded", "critical", "recovering"]


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_snapshot(name: str) -> dict:
    path = SNAPSHOT_DIR / name
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {"health": "unknown", "worker": name.replace("_snapshot.json", ""), "timestamp": None}


def _aggregate_health(snapshots: list) -> str:
    worst = 0
    for s in snapshots:
        h = s.get("health", "unknown")
        worst = max(worst, HEALTH_RANK.get(h, 1))

    if worst == 0:
        return "HEALTHY"
    elif worst == 1:
        return "HEALTHY"
    elif worst == 2:
        return "WARNING"
    elif worst == 3:
        return "DEGRADED"
    else:
        return "CRITICAL"


def _collect_all_issues(snapshots: list) -> list:
    all_issues = []
    for s in snapshots:
        worker = s.get("worker", "unknown")
        for issue in s.get("issues", []):
            all_issues.append({**issue, "worker": worker})
    return all_issues


def _count_by_severity(issues: list) -> dict:
    counts = {"critical": 0, "warning": 0, "info": 0}
    for i in issues:
        sev = i.get("severity", "info")
        counts[sev] = counts.get(sev, 0) + 1
    return counts


def _load_provider_health() -> dict:
    f = Path("memory/provider_health.json")
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    snapshots = [_load_snapshot(name) for name in WORKER_SNAPSHOTS]
    all_issues = _collect_all_issues(snapshots)
    system_health = _aggregate_health(snapshots)
    issue_counts = _count_by_severity(all_issues)
    provider_health = _load_provider_health()

    # Workers that have never run or are stale
    missing_workers = [
        s["worker"] for s in snapshots
        if s.get("health") == "unknown" or not s.get("timestamp")
    ]

    if missing_workers and system_health == "HEALTHY":
        system_health = "WARNING"

    # Build per-worker summary
    worker_summary = []
    for s in snapshots:
        worker_summary.append({
            "worker": s.get("worker", "unknown"),
            "health": s.get("health", "unknown"),
            "timestamp": s.get("timestamp"),
            "issue_count": len(s.get("issues", [])),
        })

    snapshot = {
        "worker": "telemetry_worker",
        "timestamp": _now(),
        "system_health": system_health,
        "worker_summary": worker_summary,
        "missing_workers": missing_workers,
        "all_issues": all_issues,
        "issue_counts": issue_counts,
        "total_issues": len(all_issues),
        "provider_health": {
            "openai": provider_health.get("openai", {}).get("status", "unknown"),
            "gemini": provider_health.get("gemini", {}).get("status", "unknown"),
        },
        "health": system_health.lower(),
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))

    # Also write as the canonical system health file
    SYSTEM_HEALTH_FILE.write_text(json.dumps({
        "system_health": system_health,
        "timestamp": _now(),
        "issue_counts": issue_counts,
        "provider_openai": provider_health.get("openai", {}).get("status", "unknown"),
        "provider_gemini": provider_health.get("gemini", {}).get("status", "unknown"),
        "worker_count": len(snapshots),
        "missing_workers": missing_workers,
    }, indent=2))

    print(f"[telemetry_worker] system_health={system_health} issues={len(all_issues)}")
    return snapshot


if __name__ == "__main__":
    run()
