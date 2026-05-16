"""Games worker — reads factory/QA reports, tracks generation rate, detects issues."""
import json
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
FACTORY_REPORT = Path("memory/game_factory_report.json")
QA_REPORT = Path("memory/game_qa_report.json")
GAMES_DIR = Path("outputs/yallaplays/games")
OUTPUT_FILE = SNAPSHOT_DIR / "games_snapshot.json"

TARGET_GAMES = 30
QA_THRESHOLD = 75
MIN_PASS_RATE_PCT = 70


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _count_games() -> int:
    if not GAMES_DIR.exists():
        return 0
    return len([d for d in GAMES_DIR.iterdir() if d.is_dir()])


def _count_qa_results() -> dict:
    qa_dir = Path("memory/qa_results")
    if not qa_dir.exists():
        return {"total": 0, "passed": 0, "failed": 0}
    total = passed = failed = 0
    for f in qa_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text())
            score = data.get("score", 0)
            total += 1
            if score >= QA_THRESHOLD:
                passed += 1
            else:
                failed += 1
        except Exception:
            pass
    return {"total": total, "passed": passed, "failed": failed}


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    factory = _load_json(FACTORY_REPORT)
    qa_report = _load_json(QA_REPORT)

    total_games = _count_games()
    qa_counts = _count_qa_results()

    issues = []
    opportunities = []

    # Generation progress
    progress_pct = (total_games / TARGET_GAMES * 100) if TARGET_GAMES else 0
    if total_games < TARGET_GAMES:
        opportunities.append({
            "type": "generate_more_games",
            "detail": f"{total_games}/{TARGET_GAMES} games generated ({progress_pct:.1f}%)",
        })

    # QA pass rate
    pass_rate = 0.0
    if qa_counts["total"] > 0:
        pass_rate = qa_counts["passed"] / qa_counts["total"] * 100
        if pass_rate < MIN_PASS_RATE_PCT:
            issues.append({
                "type": "low_qa_pass_rate",
                "severity": "warning",
                "detail": f"QA pass rate {pass_rate:.1f}% below {MIN_PASS_RATE_PCT}%",
            })

    # Factory errors
    factory_errors = factory.get("errors", [])
    if len(factory_errors) > 3:
        issues.append({
            "type": "factory_errors",
            "severity": "warning",
            "detail": f"{len(factory_errors)} game generation errors in factory",
        })

    # Average QA score
    avg_score = qa_report.get("avg_score", 0) or 0

    health = "healthy"
    if any(i["severity"] == "warning" for i in issues):
        health = "warning"

    snapshot = {
        "worker": "games_worker",
        "timestamp": _now(),
        "status": "ok",
        "total_games": total_games,
        "target_games": TARGET_GAMES,
        "progress_pct": round(progress_pct, 1),
        "qa_total": qa_counts["total"],
        "qa_passed": qa_counts["passed"],
        "qa_failed": qa_counts["failed"],
        "qa_pass_rate_pct": round(pass_rate, 1),
        "avg_qa_score": avg_score,
        "factory_errors": len(factory_errors),
        "issues": issues,
        "opportunities": opportunities,
        "health": health,
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[games_worker] done — {total_games} games pass_rate={pass_rate:.1f}% health={health}")
    return snapshot


if __name__ == "__main__":
    run()
