"""Indexing worker — reads indexing state, checks quota, detects issues."""
import json
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
INDEXING_REPORT = Path("memory/indexing_report.json")
INDEXING_DIR = Path("memory/indexing")
OUTPUT_FILE = SNAPSHOT_DIR / "indexing_snapshot.json"

DAILY_QUOTA = 200
QUOTA_WARN_PCT = 80


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_report() -> dict:
    if INDEXING_REPORT.exists():
        try:
            return json.loads(INDEXING_REPORT.read_text())
        except Exception:
            pass
    return {}


def _load_queue() -> list:
    q = INDEXING_DIR / "queue.json"
    if q.exists():
        try:
            return json.loads(q.read_text())
        except Exception:
            pass
    return []


def _load_failed() -> list:
    f = INDEXING_DIR / "failed.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return []


def _load_submitted() -> list:
    s = INDEXING_DIR / "submitted.json"
    if s.exists():
        try:
            return json.loads(s.read_text())
        except Exception:
            pass
    return []


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    report = _load_report()
    queue = _load_queue()
    failed = _load_failed()
    submitted = _load_submitted()

    issues = []
    today_submitted = report.get("today_submitted", 0)
    quota_used_pct = (today_submitted / DAILY_QUOTA * 100) if DAILY_QUOTA else 0

    if quota_used_pct >= QUOTA_WARN_PCT:
        issues.append({
            "type": "quota_near_limit",
            "severity": "warning",
            "detail": f"Daily quota {today_submitted}/{DAILY_QUOTA} ({quota_used_pct:.1f}%)",
        })

    if len(failed) > 10:
        issues.append({
            "type": "high_failure_count",
            "severity": "warning",
            "detail": f"{len(failed)} URLs in failed queue",
        })

    if len(queue) > 50:
        issues.append({
            "type": "large_queue_backlog",
            "severity": "info",
            "detail": f"{len(queue)} URLs pending in queue",
        })

    snapshot = {
        "worker": "indexing_worker",
        "timestamp": _now(),
        "status": "ok",
        "queue_size": len(queue),
        "failed_count": len(failed),
        "submitted_today": today_submitted,
        "total_submitted": len(submitted),
        "quota_used_pct": round(quota_used_pct, 1),
        "quota_remaining": DAILY_QUOTA - today_submitted,
        "issues": issues,
        "health": "warning" if issues else "healthy",
        "last_report_updated": report.get("generated_at"),
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[indexing_worker] done — queue={len(queue)} failed={len(failed)} health={snapshot['health']}")
    return snapshot


if __name__ == "__main__":
    run()
