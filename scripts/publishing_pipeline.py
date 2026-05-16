"""
MIFTEH OS — Publishing Pipeline Orchestrator
Tracks the full lifecycle of each game through the publishing pipeline.
Steps: generate → qa → assets → seo → approval → pr → deploy → index → track
NEVER auto-deploys — admin approval is mandatory at the approval gate.
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

try:
    from telegram_notifier import (send_system_log, send_admin_alert,
                                   send_approval_request, notify_workflow_complete)
except Exception:
    def send_system_log(*a, **kw): pass
    def send_admin_alert(*a, **kw): pass
    def send_approval_request(*a, **kw): pass
    def notify_workflow_complete(*a, **kw): pass

MEMORY_DIR = Path("memory")
PIPELINE_DIR = MEMORY_DIR / "publishing_pipeline"
REVIEWS_DIR = MEMORY_DIR / "reviews"
PIPELINE_REPORT_FILE = MEMORY_DIR / "publishing_pipeline_report.json"

YALLAPLAYS_BASE_URL = os.environ.get("YALLAPLAYS_BASE_URL", "https://yallaplays.com")
YALLAPLAYS_REPO = os.environ.get("REPO_YALLAPLAYS", "")

# Pipeline step order and display labels
PIPELINE_STEPS = [
    ("generate",     "Game Generation",         "🎮"),
    ("qa_check",     "QA Validation",            "✅"),
    ("asset_gen",    "Asset Generation",         "🖼"),
    ("seo_page",     "SEO Page Creation",        "📄"),
    ("internal_link","Internal Link Injection",  "🔗"),
    ("sitemap",      "Sitemap Entry",            "🗺"),
    ("approval",     "Admin Approval",           "👤"),
    ("pr_created",   "PR Created",               "📋"),
    ("deployed",     "Deployed to Production",   "🚀"),
    ("indexed",      "Google Indexed",           "🔍"),
    ("tracking",     "CTR/Engagement Tracking",  "📊"),
]

STEP_IDS = [s[0] for s in PIPELINE_STEPS]

MONETIZATION_CONFIG = {
    "adsense_placement_zones": ["above-game", "below-game", "sidebar-desktop", "interstitial-mobile"],
    "target_session_duration_sec": 180,
    "replay_trigger": "game_over",
    "recommended_games_count": 6,
    "sticky_mobile_ad": True,
    "min_rpm_target_usd": 0.80,
    "max_rpm_target_usd": 3.50,
}


# ─── Pipeline state per game ─────────────────────────────────────────────────

def _load_pipeline_state(game_id: str) -> dict:
    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    state_file = PIPELINE_DIR / f"{game_id}.json"
    if state_file.exists():
        try:
            return json.loads(state_file.read_text())
        except Exception:
            pass
    return {"game_id": game_id, "steps": {}, "created_at": now_iso(), "status": "in_progress"}


def _save_pipeline_state(state: dict):
    game_id = state["game_id"]
    state["updated_at"] = now_iso()
    (PIPELINE_DIR / f"{game_id}.json").write_text(
        json.dumps(state, indent=2, ensure_ascii=False)
    )


def _mark_step(state: dict, step_id: str, status: str, detail: str = "", extra: dict = None):
    state["steps"][step_id] = {
        "status": status,
        "detail": detail,
        "extra": extra or {},
        "timestamp": now_iso(),
    }
    _save_pipeline_state(state)


def _completed_steps(state: dict) -> list[str]:
    return [k for k, v in state.get("steps", {}).items() if v.get("status") == "done"]


def _step_done(state: dict, step_id: str) -> bool:
    return state.get("steps", {}).get(step_id, {}).get("status") == "done"


# ─── Review loader ────────────────────────────────────────────────────────────

def _load_all_reviews() -> list[dict]:
    if not REVIEWS_DIR.exists():
        return []
    reviews = []
    for f in sorted(REVIEWS_DIR.glob("rev_*.json")):
        try:
            r = json.loads(f.read_text())
            reviews.append(r)
        except Exception:
            pass
    return reviews


# ─── Step checkers ────────────────────────────────────────────────────────────

def _check_asset_step(game_id: str) -> bool:
    asset_dir = Path("outputs/yallaplays/assets") / game_id
    return (asset_dir / "thumbnail.svg").exists() and (asset_dir / "og-image.svg").exists()


def _check_seo_step(game_id: str) -> bool:
    seo_file = Path("outputs/yallaplays/game_seo") / f"seo_{game_id}.json"
    return seo_file.exists()


def _check_indexed_step(game_id: str) -> bool:
    indexed_file = MEMORY_DIR / "indexing" / "indexed_urls.json"
    if not indexed_file.exists():
        return False
    try:
        data = json.loads(indexed_file.read_text())
        indexed_urls = {u.get("url", "") for u in data.get("urls", [])}
        game_url = f"{YALLAPLAYS_BASE_URL}/games/{game_id}/"
        return game_url in indexed_urls
    except Exception:
        return False


# ─── AI pipeline analysis ─────────────────────────────────────────────────────

def ai_analyze_pipeline(reviews: list[dict], pipeline_states: list[dict]) -> dict:
    if not reviews:
        return {}

    pending_count = sum(1 for r in reviews if r.get("status") == "pending_review")
    deployed_count = sum(1 for r in reviews if r.get("status") == "deployed")
    eligible_count = sum(1 for r in reviews if r.get("qa_eligible"))

    system = "You are the publishing pipeline AI for YallaPlays gaming platform."
    prompt = f"""Analyze the publishing pipeline state and provide optimization recommendations.

Stats:
- Total games: {len(reviews)}
- Pending review: {pending_count}
- QA eligible: {eligible_count}
- Deployed: {deployed_count}
- Pipeline states tracked: {len(pipeline_states)}

Top bottlenecks based on step completion rates:
{json.dumps({s[0]: sum(1 for p in pipeline_states if _step_done_from_steps(p, s[0])) for s in PIPELINE_STEPS}, ensure_ascii=False)}

Respond with JSON:
{{
  "pipeline_health": "healthy|needs_attention|critical",
  "bottleneck_step": "step_id",
  "throughput_estimate": "X games/week",
  "revenue_estimate_usd": 0,
  "top_priorities": ["p1", "p2", "p3"],
  "seo_velocity": "slow|normal|fast",
  "monetization_readiness": 0
}}"""

    result, _, _, ok = generate_json(system, prompt, 400)
    if ok and isinstance(result, dict):
        return result
    return {"pipeline_health": "unknown", "bottleneck_step": "unknown", "top_priorities": []}


def _step_done_from_steps(pipeline_state: dict, step_id: str) -> bool:
    return pipeline_state.get("steps", {}).get(step_id, {}).get("status") == "done"


# ─── Sync reviews to pipeline states ─────────────────────────────────────────

def sync_review_to_pipeline(review: dict) -> dict:
    """Create/update pipeline state from review entry."""
    game_id = review.get("game_id", review.get("review_id", ""))
    if not game_id:
        return {}

    state = _load_pipeline_state(game_id)
    state["review_id"] = review.get("review_id", "")
    state["game_type"] = review.get("game_type", "")
    state["name"] = review.get("name", "")
    state["qa_score"] = review.get("qa_score", 0)
    state["review_status"] = review.get("status", "")

    # Infer completed steps from review status
    status = review.get("status", "")

    if status in ("pending_review", "approved", "rejected", "deployed", "rolled_back"):
        _mark_step(state, "generate", "done", "Game generated by game_factory.py")

    if review.get("qa_score") is not None:
        qa_status = "done" if review.get("qa_eligible") else "failed"
        _mark_step(state, "qa_check", qa_status, f"QA score: {review.get('qa_score')}/100")

    if _check_asset_step(game_id):
        _mark_step(state, "asset_gen", "done", "Thumbnail + OG image generated")

    if _check_seo_step(game_id):
        _mark_step(state, "seo_page", "done", "SEO page generated")

    if status == "approved":
        _mark_step(state, "approval", "done", "Admin approved")

    if review.get("pr_url"):
        _mark_step(state, "pr_created", "done", review.get("pr_url", ""), {"pr_url": review["pr_url"]})

    if status == "deployed":
        _mark_step(state, "deployed", "done", review.get("deploy_url", ""))

    if _check_indexed_step(game_id):
        _mark_step(state, "indexed", "done", f"{YALLAPLAYS_BASE_URL}/games/{game_id}/")

    # Compute overall completion %
    done = len(_completed_steps(state))
    total_steps = len(PIPELINE_STEPS)
    state["completion_pct"] = round(100 * done / total_steps)
    state["steps_done"] = done
    state["steps_total"] = total_steps

    _save_pipeline_state(state)
    return state


# ─── SEO score + CTR/RPM estimates ───────────────────────────────────────────

def _compute_seo_score(game_id: str, game_type: str, qa_score: int) -> int:
    """Estimate SEO score 0-100 from available signals."""
    score = 0
    if _check_seo_step(game_id):
        score += 40
    seo_file = Path("outputs/yallaplays/game_seo") / f"seo_{game_id}.json"
    if seo_file.exists():
        try:
            seo = json.loads(seo_file.read_text())
            if seo.get("seo_ar", {}).get("faq"):
                score += 15
            if seo.get("schemas", {}).get("video_game"):
                score += 15
            if seo.get("seo_ar", {}).get("keywords"):
                score += 10
        except Exception:
            pass
    if _check_asset_step(game_id):
        score += 10  # OG image helps CTR
    if qa_score >= 75:
        score += 10  # Quality signal
    return min(score, 100)


def _estimate_ctr(game_type: str, qa_score: int, seo_score: int) -> str:
    """Estimate organic CTR based on game type and scores."""
    base_ctr = {"racing": 4.2, "car": 3.8, "drift": 3.5, "action": 3.9,
                "survival": 3.2, "clicker": 3.6, "idle": 3.4,
                "puzzle": 4.5, "kids": 5.1, "brain": 3.7}
    base = base_ctr.get(game_type, 3.5)
    modifier = (qa_score / 100) * 0.5 + (seo_score / 100) * 0.5
    estimated = round(base * modifier, 1)
    return f"{estimated}%"


def _estimate_rpm(game_type: str) -> str:
    """Estimate ad RPM based on game type."""
    rpm_map = {"racing": 1.20, "car": 1.15, "drift": 1.10, "action": 1.25,
               "survival": 0.95, "clicker": 0.85, "idle": 0.90,
               "puzzle": 1.40, "kids": 1.80, "brain": 1.35}
    rpm = rpm_map.get(game_type, 1.00)
    return f"${rpm:.2f}"


# ─── Enhanced Telegram approval ───────────────────────────────────────────────

def send_enhanced_approval(review: dict, seo_score: int, ctr_estimate: str, rpm_estimate: str):
    """Send admin Telegram alert with full pipeline data."""
    game_id = review.get("game_id", "")
    try:
        from telegram_notifier import _send, ADMIN_TOKEN, ADMIN_CHAT_ID
        qa_score = review.get("qa_score", 0)
        qa_emoji = "🟢" if qa_score >= 75 else ("🟡" if qa_score >= 50 else "🔴")
        seo_emoji = "🟢" if seo_score >= 60 else ("🟡" if seo_score >= 40 else "🔴")
        preview_url = f"{YALLAPLAYS_BASE_URL}/preview/{game_id}/" if game_id else "pending"

        text = f"""🎮 <b>APPROVAL REQUIRED — YallaPlays Game</b>

<b>Project:</b> yallaplays
<b>Game:</b> {review.get('name', 'Unnamed')}
<b>Type:</b> {review.get('game_type', 'unknown')}
<b>Review ID:</b> <code>{review.get('review_id', '')}</code>

{qa_emoji} <b>QA Score:</b> {qa_score}/100 {"✅ ELIGIBLE" if review.get('qa_eligible') else "❌ BELOW 75"}
{seo_emoji} <b>SEO Score:</b> {seo_score}/100
🎯 <b>Estimated CTR:</b> {ctr_estimate}
💰 <b>Estimated RPM:</b> {rpm_estimate}
📑 <b>Indexing Status:</b> {"✅ Queued" if _check_indexed_step(game_id) else "⏳ Pending approval"}

🔗 <b>Preview:</b> {preview_url}
📋 <b>PR:</b> {review.get('pr_url', '⏳ Pending')}

{"✅ Ready for approval — QA ≥ 75" if review.get('qa_eligible') else "⚠️ QA score below 75 — review carefully before approving"}"""

        _send(ADMIN_TOKEN, ADMIN_CHAT_ID, text)
    except Exception as e:
        print(f"[pipeline] Enhanced approval send failed: {e}")
        send_approval_request(review)


# ─── Main pipeline runner ────────────────────────────────────────────────────

def main():
    print("[pipeline] Publishing pipeline sync starting...")
    send_system_log("workflow_started", "Publishing Pipeline Orchestrator started", "info", {"phase": "M"})

    PIPELINE_DIR.mkdir(parents=True, exist_ok=True)
    reviews = _load_all_reviews()
    print(f"[pipeline] Found {len(reviews)} reviews")

    pipeline_states = []
    approved_count = 0
    deployed_count = 0
    pending_approval_count = 0

    for review in reviews:
        game_id = review.get("game_id", review.get("review_id", ""))
        if not game_id:
            continue

        state = sync_review_to_pipeline(review)
        if state:
            pipeline_states.append(state)

        # Send enhanced approval notifications for eligible pending items
        if (review.get("status") == "pending_review" and
                review.get("qa_eligible") and
                not review.get("approval_notified")):
            game_type = review.get("game_type", "racing")
            qa_score = review.get("qa_score", 0)
            seo_score = _compute_seo_score(game_id, game_type, qa_score)
            ctr = _estimate_ctr(game_type, qa_score, seo_score)
            rpm = _estimate_rpm(game_type)
            send_enhanced_approval(review, seo_score, ctr, rpm)
            pending_approval_count += 1

            # Mark as notified in review file
            review_file = REVIEWS_DIR / f"rev_{review.get('review_id', game_id)}.json"
            if review_file.exists():
                review["approval_notified"] = True
                review_file.write_text(json.dumps(review, indent=2, ensure_ascii=False))

        if review.get("status") == "approved":
            approved_count += 1
        if review.get("status") == "deployed":
            deployed_count += 1

    # AI analysis
    ai_analysis = ai_analyze_pipeline(reviews, pipeline_states)

    # Build per-step summary
    step_summary = {}
    for step_id, label, emoji in PIPELINE_STEPS:
        done = sum(1 for p in pipeline_states if _step_done_from_steps(p, step_id))
        step_summary[step_id] = {
            "label": label,
            "emoji": emoji,
            "done": done,
            "total": len(pipeline_states),
            "completion_pct": round(100 * done / max(len(pipeline_states), 1)),
        }

    # Revenue estimates
    avg_rpm = 1.20  # USD
    avg_session_min = 3.5
    games_deployed = deployed_count
    est_monthly_sessions_per_game = 500
    est_monthly_revenue = games_deployed * est_monthly_sessions_per_game * avg_rpm / 1000

    report = {
        "generated_at": now_iso(),
        "total_games": len(reviews),
        "pending_approval": pending_approval_count,
        "approved": approved_count,
        "deployed": deployed_count,
        "pipeline_states": len(pipeline_states),
        "pipeline_health": ai_analysis.get("pipeline_health", "unknown"),
        "bottleneck_step": ai_analysis.get("bottleneck_step", "unknown"),
        "throughput_estimate": ai_analysis.get("throughput_estimate", ""),
        "monetization": {
            "config": MONETIZATION_CONFIG,
            "deployed_games": games_deployed,
            "est_monthly_revenue_usd": round(est_monthly_revenue, 2),
            "est_rpm": f"${avg_rpm:.2f}",
            "est_session_min": avg_session_min,
        },
        "seo_velocity": ai_analysis.get("seo_velocity", "normal"),
        "top_priorities": ai_analysis.get("top_priorities", []),
        "step_summary": step_summary,
        "games": [
            {
                "game_id": p.get("game_id"),
                "name": p.get("name"),
                "game_type": p.get("game_type"),
                "review_status": p.get("review_status"),
                "qa_score": p.get("qa_score"),
                "completion_pct": p.get("completion_pct", 0),
                "steps_done": p.get("steps_done", 0),
                "steps_total": p.get("steps_total", len(PIPELINE_STEPS)),
            }
            for p in pipeline_states
        ],
    }

    PIPELINE_REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[pipeline] Done — {len(reviews)} games tracked, {pending_approval_count} notified, "
          f"{approved_count} approved, {deployed_count} deployed")

    send_system_log("workflow_completed",
                    f"Pipeline sync done — {len(reviews)} games, {deployed_count} live",
                    "success",
                    {"total": len(reviews), "deployed": deployed_count,
                     "health": report["pipeline_health"]})
    return report


if __name__ == "__main__":
    main()
