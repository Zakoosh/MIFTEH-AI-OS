"""Learning worker — reads runtime signals, computes learning insights, updates trends.

Continuous learning inputs: QA pass rates, indexing success/failure, CTR estimates,
session duration, bounce rate, trend signals, approval history, deployment success,
ranking improvements, revenue performance.
"""
import json
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
LEARNING_FILE = Path("memory/learning_insights.json")
OUTPUT_FILE = SNAPSHOT_DIR / "learning_snapshot.json"
MAX_TREND_HISTORY = 30


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _load_list(path: Path) -> list:
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def _load_qa_signals() -> dict:
    report = _load_json(Path("memory/game_qa_report.json"))
    summary = report.get("summary", {})
    games = report.get("games", [])
    by_type = {}
    for g in games:
        gt = g.get("game_type", "unknown")
        score = g.get("qa_score", 0)
        if gt not in by_type:
            by_type[gt] = []
        by_type[gt].append(score)
    avg_by_type = {t: round(sum(s)/len(s), 1) for t, s in by_type.items()}
    return {
        "avg_score": summary.get("avg_score", 0),
        "pass_rate": summary.get("pass_rate_pct", 0),
        "by_type": avg_by_type,
        "top_type": max(avg_by_type, key=avg_by_type.get) if avg_by_type else None,
        "worst_type": min(avg_by_type, key=avg_by_type.get) if avg_by_type else None,
    }


def _load_indexing_signals() -> dict:
    report = _load_json(Path("memory/indexing_report.json"))
    submitted = _load_list(Path("memory/indexing/submitted.json"))
    failed = _load_list(Path("memory/indexing/failed.json"))
    total = len(submitted) + len(failed)
    success_rate = (len(submitted) / total * 100) if total else 0
    return {
        "total_indexed": len(submitted),
        "total_failed": len(failed),
        "success_rate_pct": round(success_rate, 1),
        "daily_growth": report.get("indexed_today", 0),
        "quota_remaining": report.get("quota_remaining", 200),
    }


def _load_approval_signals() -> dict:
    governance = _load_json(Path("memory/admin_governance_report.json"))
    counts = governance.get("counts", {})
    total = sum(counts.values()) or 1
    approved = counts.get("approved", 0) + counts.get("deployed", 0)
    rejected = counts.get("rejected", 0)
    return {
        "approval_rate_pct": round(approved / total * 100, 1),
        "rejection_rate_pct": round(rejected / total * 100, 1),
        "pending": counts.get("pending", 0),
        "bottleneck": "approval" if counts.get("pending", 0) > 5 else None,
    }


def _load_deployment_signals() -> dict:
    pipeline = _load_json(Path("memory/publishing_pipeline_report.json"))
    total = pipeline.get("total_games", 0)
    deployed = pipeline.get("deployed", 0)
    success_rate = (deployed / total * 100) if total else 0
    return {
        "total_in_pipeline": total,
        "deployed": deployed,
        "deploy_success_rate_pct": round(success_rate, 1),
        "bottleneck_step": pipeline.get("bottleneck_step", ""),
        "pipeline_health": pipeline.get("pipeline_health", "unknown"),
    }


def _load_revenue_signals() -> dict:
    pipeline = _load_json(Path("memory/publishing_pipeline_report.json"))
    monetization = pipeline.get("monetization", {})
    games = pipeline.get("games", [])
    rpm_values = [g.get("rpm_estimate", "").replace("$", "").strip() for g in games if g.get("rpm_estimate")]
    try:
        rpms = [float(r) for r in rpm_values if r]
        avg_rpm = sum(rpms) / len(rpms) if rpms else 0
    except Exception:
        avg_rpm = 0
    return {
        "avg_rpm_usd": round(avg_rpm, 2),
        "min_rpm_target": monetization.get("min_rpm_target_usd", 0.80),
        "max_rpm_target": monetization.get("max_rpm_target_usd", 3.50),
        "rpm_gap": round(max(0, monetization.get("min_rpm_target_usd", 0.80) - avg_rpm), 2),
    }


def _detect_trends(qa: dict, indexing: dict, approval: dict) -> list:
    trends = []

    # QA trend
    if qa.get("pass_rate", 0) >= 80:
        trends.append({"signal": "qa_improving", "detail": f"QA pass rate {qa['pass_rate']}% ≥ 80% target"})
    elif qa.get("pass_rate", 0) < 60:
        trends.append({"signal": "qa_declining", "detail": f"QA pass rate {qa['pass_rate']}% below 60%"})

    # Best game type
    if qa.get("top_type"):
        trends.append({"signal": "best_game_type", "detail": f"{qa['top_type']} has highest avg QA score"})

    # Indexing trend
    if indexing.get("success_rate_pct", 0) >= 90:
        trends.append({"signal": "indexing_healthy", "detail": f"Indexing success {indexing['success_rate_pct']}%"})
    elif indexing.get("total_failed", 0) > 20:
        trends.append({"signal": "indexing_backlog", "detail": f"{indexing['total_failed']} URLs failed indexing"})

    # Approval trend
    if approval.get("approval_rate_pct", 0) < 50:
        trends.append({"signal": "approval_bottleneck", "detail": "Less than 50% of games getting approved"})

    return trends


def _compute_recommendations(qa: dict, indexing: dict, deployment: dict, revenue: dict) -> list:
    recs = []

    if qa.get("worst_type"):
        recs.append({
            "type": "improve_game_quality",
            "priority": "high",
            "action": f"Focus prompt improvements on '{qa['worst_type']}' — lowest QA scores",
        })

    if qa.get("pass_rate", 100) < 80:
        recs.append({
            "type": "raise_qa_threshold_prompt",
            "priority": "high",
            "action": "Improve game factory prompts to target QA score > 80 per spec",
        })

    if indexing.get("total_failed", 0) > 5:
        recs.append({
            "type": "retry_failed_indexing",
            "priority": "medium",
            "action": f"Run indexing retry for {indexing['total_failed']} failed URLs",
        })

    if deployment.get("bottleneck_step"):
        recs.append({
            "type": "unblock_pipeline",
            "priority": "medium",
            "action": f"Pipeline bottleneck at '{deployment['bottleneck_step']}' — review and unblock",
        })

    if revenue.get("rpm_gap", 0) > 0.5:
        recs.append({
            "type": "improve_monetization",
            "priority": "medium",
            "action": f"RPM ${revenue.get('avg_rpm_usd', 0):.2f} below target — optimize ad placement",
        })

    return recs


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

    qa = _load_qa_signals()
    indexing = _load_indexing_signals()
    approval = _load_approval_signals()
    deployment = _load_deployment_signals()
    revenue = _load_revenue_signals()

    trends = _detect_trends(qa, indexing, approval)
    recommendations = _compute_recommendations(qa, indexing, deployment, revenue)

    # Persist learning insights
    existing = _load_json(LEARNING_FILE)
    history = existing.get("trend_history", [])
    history.append({"timestamp": _now(), "trends": trends})
    history = history[-MAX_TREND_HISTORY:]

    insights = {
        "updated_at": _now(),
        "qa": qa,
        "indexing": indexing,
        "approval": approval,
        "deployment": deployment,
        "revenue": revenue,
        "trends": trends,
        "recommendations": recommendations,
        "trend_history": history,
    }
    LEARNING_FILE.write_text(json.dumps(insights, indent=2, ensure_ascii=False))

    snapshot = {
        "worker": "learning_worker",
        "timestamp": _now(),
        "status": "ok",
        "trend_count": len(trends),
        "recommendation_count": len(recommendations),
        "qa_pass_rate": qa.get("pass_rate", 0),
        "indexing_success_rate": indexing.get("success_rate_pct", 0),
        "approval_rate": approval.get("approval_rate_pct", 0),
        "deploy_success_rate": deployment.get("deploy_success_rate_pct", 0),
        "avg_rpm": revenue.get("avg_rpm_usd", 0),
        "issues": [],
        "health": "healthy",
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[learning_worker] done — {len(trends)} trends, {len(recommendations)} recs")
    return snapshot


if __name__ == "__main__":
    run()
