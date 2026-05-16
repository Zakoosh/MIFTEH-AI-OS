"""Publishing worker — reads pipeline state, tracks approval bottlenecks."""
import json
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
PIPELINE_DIR = Path("memory/publishing_pipeline")
PIPELINE_REPORT = Path("memory/publishing_pipeline_report.json")
GOVERNANCE_REPORT = Path("memory/admin_governance_report.json")
OUTPUT_FILE = SNAPSHOT_DIR / "publishing_snapshot.json"

APPROVAL_BOTTLENECK_THRESHOLD = 5  # games waiting > N days = bottleneck


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _load_pipeline_states() -> list:
    if not PIPELINE_DIR.exists():
        return []
    states = []
    for f in PIPELINE_DIR.glob("*.json"):
        try:
            states.append(json.loads(f.read_text()))
        except Exception:
            pass
    return states


def _step_completion_rate(states: list) -> float:
    if not states:
        return 0.0
    total_steps = 11  # PIPELINE_STEPS count
    total_possible = len(states) * total_steps
    total_completed = sum(len(s.get("completed_steps", [])) for s in states)
    return (total_completed / total_possible * 100) if total_possible else 0.0


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    report = _load_json(PIPELINE_REPORT)
    governance = _load_json(GOVERNANCE_REPORT)
    pipeline_states = _load_pipeline_states()

    issues = []

    total_games = len(pipeline_states)
    pending_approval = sum(
        1 for s in pipeline_states
        if s.get("current_step") == "approval" or s.get("status") == "pending_review"
    )
    deployed = sum(1 for s in pipeline_states if "deployed" in s.get("completed_steps", []))
    blocked = sum(1 for s in pipeline_states if s.get("status") == "qa_failed")
    completion_rate = _step_completion_rate(pipeline_states)

    if pending_approval >= APPROVAL_BOTTLENECK_THRESHOLD:
        issues.append({
            "type": "approval_bottleneck",
            "severity": "warning",
            "detail": f"{pending_approval} games waiting for approval",
        })

    if blocked > 0:
        issues.append({
            "type": "qa_failures",
            "severity": "info",
            "detail": f"{blocked} games blocked by QA failures",
        })

    # Check governance queue
    pending_reviews = governance.get("pending_count", 0)
    if pending_reviews > 10:
        issues.append({
            "type": "large_review_queue",
            "severity": "warning",
            "detail": f"{pending_reviews} items in admin review queue",
        })

    health = "healthy"
    if any(i["severity"] == "warning" for i in issues):
        health = "warning"
    if any(i["severity"] == "critical" for i in issues):
        health = "critical"

    snapshot = {
        "worker": "publishing_worker",
        "timestamp": _now(),
        "status": "ok",
        "total_games_in_pipeline": total_games,
        "deployed_count": deployed,
        "pending_approval": pending_approval,
        "blocked_by_qa": blocked,
        "completion_rate_pct": round(completion_rate, 1),
        "pending_reviews": pending_reviews,
        "issues": issues,
        "health": health,
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[publishing_worker] done — deployed={deployed} pending={pending_approval} health={health}")
    return snapshot


if __name__ == "__main__":
    run()
