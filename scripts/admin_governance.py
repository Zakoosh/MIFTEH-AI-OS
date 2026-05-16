"""
MIFTEH OS — Admin Governance Engine
Manages the review queue: pending → approved/rejected → deployed/rolled_back.
Reads all reviews from memory/reviews/, produces the admin dashboard report.
Does NOT auto-merge — all approvals require explicit admin action.
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

try:
    from telegram_notifier import send_system_log, send_admin_alert, send_approval_request
except Exception:
    def send_system_log(*a, **kw): pass
    def send_admin_alert(*a, **kw): pass
    def send_approval_request(*a, **kw): pass

MEMORY_DIR = Path("memory")
REVIEWS_DIR = MEMORY_DIR / "reviews"
APPROVALS_DIR = MEMORY_DIR / "approvals"
REJECTIONS_DIR = MEMORY_DIR / "rejections"
DEPLOYMENTS_DIR = MEMORY_DIR / "deployments"

GOVERNANCE_REPORT = MEMORY_DIR / "admin_governance_report.json"
APPROVAL_QUEUE_FILE = MEMORY_DIR / "approval_queue.json"
AUDIT_LOG_FILE = MEMORY_DIR / "audit_log.json"

QA_THRESHOLD = 75
MAX_AUDIT_ENTRIES = 500

# Status flow: generated → pending_review → approved/rejected → deployed/rolled_back
VALID_STATUSES = {"generated", "pending_review", "qa_failed", "approved", "rejected", "deployed", "rolled_back"}


# ─── Audit log ───────────────────────────────────────────────────────────────────

def _append_audit(action: str, item_id: str, actor: str, detail: str, extra: dict = None):
    MEMORY_DIR.mkdir(exist_ok=True)
    log = {}
    if AUDIT_LOG_FILE.exists():
        try:
            log = json.loads(AUDIT_LOG_FILE.read_text())
        except Exception:
            log = {}
    entries = log.get("entries", [])
    entries.append({
        "timestamp": now_iso(),
        "action": action,
        "item_id": item_id,
        "actor": actor,
        "detail": detail,
        "extra": extra or {},
    })
    log["entries"] = entries[-MAX_AUDIT_ENTRIES:]
    log["updated_at"] = now_iso()
    AUDIT_LOG_FILE.write_text(json.dumps(log, indent=2, ensure_ascii=False))


# ─── Review file helpers ─────────────────────────────────────────────────────────

def _load_review(review_file: Path) -> dict | None:
    try:
        return json.loads(review_file.read_text())
    except Exception:
        return None


def _save_review(review: dict, review_file: Path):
    review["updated_at"] = now_iso()
    review_file.write_text(json.dumps(review, indent=2, ensure_ascii=False))


def _load_all_reviews() -> list[dict]:
    if not REVIEWS_DIR.exists():
        return []
    reviews = []
    for f in sorted(REVIEWS_DIR.glob("rev_*.json")):
        r = _load_review(f)
        if r:
            r["_file"] = str(f)
            reviews.append(r)
    return reviews


# ─── Queue builders ──────────────────────────────────────────────────────────────

def build_approval_queue(reviews: list[dict]) -> dict:
    pending = [r for r in reviews if r.get("status") == "pending_review"]
    qa_eligible = [r for r in pending if r.get("qa_eligible") or r.get("qa_score", 0) >= QA_THRESHOLD]
    qa_failed_pending = [r for r in pending if not (r.get("qa_eligible") or r.get("qa_score", 0) >= QA_THRESHOLD)]
    approved = [r for r in reviews if r.get("status") == "approved"]
    rejected = [r for r in reviews if r.get("status") == "rejected"]
    deployed = [r for r in reviews if r.get("status") == "deployed"]
    rolled_back = [r for r in reviews if r.get("status") == "rolled_back"]
    qa_failures = [r for r in reviews if r.get("status") == "qa_failed"]

    queue = {
        "generated_at": now_iso(),
        "pending": _slim(pending),
        "qa_eligible": _slim(qa_eligible),
        "qa_failed_pending": _slim(qa_failed_pending),
        "approved": _slim(approved),
        "rejected": _slim(rejected),
        "deployed": _slim(deployed),
        "rolled_back": _slim(rolled_back),
        "qa_failures": _slim(qa_failures),
        "counts": {
            "pending": len(pending),
            "qa_eligible": len(qa_eligible),
            "qa_failed_pending": len(qa_failed_pending),
            "approved": len(approved),
            "rejected": len(rejected),
            "deployed": len(deployed),
            "rolled_back": len(rolled_back),
            "qa_failures": len(qa_failures),
            "total": len(reviews),
        },
    }
    return queue


def _slim(reviews: list[dict]) -> list[dict]:
    keys = ["review_id", "game_id", "status", "qa_score", "qa_eligible", "game_type",
            "name", "project", "type", "created_at", "updated_at", "pr_url", "impact", "confidence"]
    return [{k: r.get(k) for k in keys} for r in reviews]


# ─── AI triage ──────────────────────────────────────────────────────────────────

def ai_triage_pending(pending: list[dict]) -> list[dict]:
    if not pending:
        return []

    system = "You are an admin AI for YallaPlays gaming platform. Triage review queue items."
    prompt = f"""Triage these {len(pending)} pending game reviews. For each, decide if it's high/medium/low priority.
High = QA score ≥ 85 AND game type in demand (racing, puzzle, kids).
Low = QA score < 60 OR game type oversaturated.

Reviews:
{json.dumps([{{k: r.get(k) for k in ['review_id','game_type','qa_score','name']}} for r in pending[:10]], ensure_ascii=False)}

Respond with JSON: {{"triage": [{{"review_id": "...", "priority": "high|medium|low", "reason": "..."}}]}}"""

    result, _, _, ok = generate_json(system, prompt, 600)
    if ok and isinstance(result, dict):
        triage_map = {t["review_id"]: t for t in result.get("triage", [])}
        for r in pending:
            t = triage_map.get(r.get("review_id"), {})
            r["ai_priority"] = t.get("priority", "medium")
            r["ai_triage_reason"] = t.get("reason", "")
    return pending


# ─── Status transitions (called by admin actions, not auto) ─────────────────────

def approve_review(review_id: str, actor: str = "admin") -> bool:
    review_file = REVIEWS_DIR / f"rev_{review_id}.json"
    if not review_file.exists():
        print(f"[governance] Review {review_id} not found")
        return False

    review = _load_review(review_file)
    if not review:
        return False

    if review.get("status") not in ("pending_review", "qa_failed"):
        print(f"[governance] Review {review_id} is in status {review.get('status')} — cannot approve")
        return False

    if not review.get("qa_eligible") and review.get("qa_score", 0) < QA_THRESHOLD:
        print(f"[governance] WARNING: Approving game with QA score {review.get('qa_score')} < {QA_THRESHOLD}")

    review["status"] = "approved"
    review["approved_by"] = actor
    review["approved_at"] = now_iso()
    _save_review(review, review_file)

    # Copy to approvals dir
    APPROVALS_DIR.mkdir(parents=True, exist_ok=True)
    (APPROVALS_DIR / f"{review_id}.json").write_text(json.dumps(review, indent=2, ensure_ascii=False))

    _append_audit("approve", review_id, actor, f"Approved {review.get('name', review_id)}", {"qa_score": review.get("qa_score")})
    send_system_log("item_approved", f"<b>{review.get('name', review_id)}</b> approved by {actor}", "success",
                    {"review_id": review_id, "qa_score": review.get("qa_score")})
    print(f"[governance] Approved: {review_id}")
    return True


def reject_review(review_id: str, reason: str, actor: str = "admin") -> bool:
    review_file = REVIEWS_DIR / f"rev_{review_id}.json"
    if not review_file.exists():
        return False

    review = _load_review(review_file)
    if not review:
        return False

    review["status"] = "rejected"
    review["rejected_by"] = actor
    review["rejected_at"] = now_iso()
    review["rejection_reason"] = reason
    _save_review(review, review_file)

    REJECTIONS_DIR.mkdir(parents=True, exist_ok=True)
    (REJECTIONS_DIR / f"{review_id}.json").write_text(json.dumps(review, indent=2, ensure_ascii=False))

    _append_audit("reject", review_id, actor, reason, {"qa_score": review.get("qa_score")})
    send_system_log("item_rejected", f"<b>{review.get('name', review_id)}</b> rejected: {reason}", "warning",
                    {"review_id": review_id})
    print(f"[governance] Rejected: {review_id} — {reason}")
    return True


def mark_deployed(review_id: str, deploy_url: str = "", actor: str = "workflow") -> bool:
    review_file = REVIEWS_DIR / f"rev_{review_id}.json"
    if not review_file.exists():
        return False

    review = _load_review(review_file)
    if not review:
        return False

    if review.get("status") != "approved":
        print(f"[governance] Review {review_id} not in approved status — cannot mark deployed")
        return False

    review["status"] = "deployed"
    review["deployed_by"] = actor
    review["deployed_at"] = now_iso()
    review["deploy_url"] = deploy_url
    _save_review(review, review_file)

    DEPLOYMENTS_DIR.mkdir(parents=True, exist_ok=True)
    (DEPLOYMENTS_DIR / f"{review_id}.json").write_text(json.dumps(review, indent=2, ensure_ascii=False))

    _append_audit("deploy", review_id, actor, f"Deployed to {deploy_url or 'production'}", {"deploy_url": deploy_url})
    send_system_log("item_deployed", f"<b>{review.get('name', review_id)}</b> deployed", "success",
                    {"review_id": review_id, "url": deploy_url})
    print(f"[governance] Deployed: {review_id}")
    return True


def rollback_review(review_id: str, reason: str, actor: str = "admin") -> bool:
    review_file = REVIEWS_DIR / f"rev_{review_id}.json"
    if not review_file.exists():
        return False

    review = _load_review(review_file)
    if not review:
        return False

    review["status"] = "rolled_back"
    review["rolled_back_by"] = actor
    review["rolled_back_at"] = now_iso()
    review["rollback_reason"] = reason
    _save_review(review, review_file)

    _append_audit("rollback", review_id, actor, reason)
    send_admin_alert("rollback_triggered", f"<b>{review.get('name', review_id)}</b> rolled back\n{reason}", "warning",
                     {"review_id": review_id})
    print(f"[governance] Rolled back: {review_id} — {reason}")
    return True


# ─── Re-notify pending approvals ────────────────────────────────────────────────

def notify_pending_approvals(reviews: list[dict]):
    eligible_pending = [r for r in reviews
                        if r.get("status") == "pending_review"
                        and r.get("qa_eligible")]
    for r in eligible_pending[:5]:  # max 5 alerts per cycle
        send_approval_request(r)
    if eligible_pending:
        send_system_log("approval_queue", f"{len(eligible_pending)} games waiting for admin approval", "warning",
                        {"count": len(eligible_pending)})


# ─── AI governance summary ───────────────────────────────────────────────────────

def ai_governance_summary(queue: dict) -> dict:
    system = "You are the AI governance officer for MIFTEH OS. Summarize the current review queue state."
    prompt = f"""Summarize this governance queue and provide strategic recommendations.
Queue counts: {json.dumps(queue.get('counts', {}), ensure_ascii=False)}
Top pending QA-eligible games: {json.dumps(queue.get('qa_eligible', [])[:3], ensure_ascii=False)}

Respond with JSON:
{{
  "health_status": "healthy|needs_attention|critical",
  "backlog_risk": "low|medium|high",
  "recommendations": ["rec1", "rec2", "rec3"],
  "estimated_deploy_ready": {queue.get('counts', {}).get('approved', 0)},
  "action_items": ["action1", "action2"]
}}"""

    result, _, _, ok = generate_json(system, prompt, 500)
    if ok and isinstance(result, dict):
        return result
    return {
        "health_status": "unknown",
        "backlog_risk": "unknown",
        "recommendations": [],
        "action_items": [],
    }


# ─── Main ────────────────────────────────────────────────────────────────────────

def main():
    send_system_log("workflow_started", "Admin Governance Engine started", "info", {"phase": "L"})

    # Ensure dirs exist
    for d in [REVIEWS_DIR, APPROVALS_DIR, REJECTIONS_DIR, DEPLOYMENTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    reviews = _load_all_reviews()
    print(f"[governance] Loaded {len(reviews)} reviews")

    # AI triage pending items
    pending = [r for r in reviews if r.get("status") == "pending_review"]
    if pending:
        ai_triage_pending(pending)

    queue = build_approval_queue(reviews)
    ai_summary = ai_governance_summary(queue)

    # Notify admins about eligible pending items
    notify_pending_approvals(reviews)

    # Build report
    report = {
        "generated_at": now_iso(),
        "queue": queue,
        "ai_summary": ai_summary,
        "recent_audit": [],
    }

    # Include last 20 audit entries in report
    if AUDIT_LOG_FILE.exists():
        try:
            audit = json.loads(AUDIT_LOG_FILE.read_text())
            report["recent_audit"] = audit.get("entries", [])[-20:]
        except Exception:
            pass

    MEMORY_DIR.mkdir(exist_ok=True)
    GOVERNANCE_REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    APPROVAL_QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False))

    counts = queue.get("counts", {})
    print(f"[governance] Done — {counts.get('pending', 0)} pending, {counts.get('approved', 0)} approved, "
          f"{counts.get('deployed', 0)} deployed, health={ai_summary.get('health_status', 'unknown')}")

    send_system_log("workflow_completed",
                    f"Admin Governance complete — {counts.get('pending', 0)} pending, "
                    f"{counts.get('approved', 0)} approved",
                    "success", counts)

    return report


if __name__ == "__main__":
    main()
