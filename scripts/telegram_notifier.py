"""
MIFTEH OS — Telegram Notifier
System logs bot (TELEGRAM_LOG_TOKEN) for all workflow events.
Admin alerts bot (TELEGRAM_ADMIN_LOG_TOKEN) for high-priority events only.
Approval messages include project, PR link, QA score, impact, approve/reject actions.
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import now_iso

MEMORY_DIR = Path("memory")
LOG_FILE = MEMORY_DIR / "telegram_logs.json"

TG_API = "https://api.telegram.org/bot"
LOG_TOKEN = os.environ.get("TELEGRAM_LOG_TOKEN", "")
ADMIN_TOKEN = os.environ.get("TELEGRAM_ADMIN_LOG_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
ADMIN_CHAT_ID = os.environ.get("TELEGRAM_ADMIN_CHAT_ID", "") or CHAT_ID

MAX_LOG_ENTRIES = 200

PRIORITY_EMOJI = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "🔴", "critical": "🚨"}


def _send(token, chat_id, text, parse_mode="HTML"):
    """Send a Telegram message. Returns (success, response)."""
    if not token or not chat_id:
        print(f"[telegram] Skipped — token/chat_id missing")
        return False, {}
    try:
        payload = json.dumps({
            "chat_id": chat_id,
            "text": text[:4096],
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }).encode()
        req = urllib.request.Request(
            f"{TG_API}{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            resp = json.loads(r.read().decode())
            return resp.get("ok", False), resp
    except Exception as e:
        print(f"[telegram] Send failed: {e}")
        return False, {"error": str(e)}


def _log(event_type, message, priority="info", extra=None):
    """Append to local telegram log."""
    LOG_FILE.parent.mkdir(exist_ok=True)
    logs = {}
    if LOG_FILE.exists():
        try:
            logs = json.loads(LOG_FILE.read_text())
        except Exception:
            logs = {}
    entries = logs.get("entries", [])
    entries.append({
        "timestamp": now_iso(),
        "event_type": event_type,
        "message": message[:500],
        "priority": priority,
        "extra": extra or {},
    })
    logs["entries"] = entries[-MAX_LOG_ENTRIES:]
    logs["updated_at"] = now_iso()
    logs["total_sent"] = logs.get("total_sent", 0) + 1
    LOG_FILE.write_text(json.dumps(logs, indent=2, ensure_ascii=False))


def send_system_log(event_type, message, priority="info", extra=None):
    """Send to system logs bot. All workflow events go here."""
    emoji = PRIORITY_EMOJI.get(priority, "ℹ️")
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    text = f"{emoji} <b>MIFTEH OS</b> [{now}]\n<b>{event_type}</b>\n{message}"
    if extra:
        for k, v in list(extra.items())[:3]:
            text += f"\n<code>{k}:</code> {v}"
    ok, _ = _send(LOG_TOKEN, CHAT_ID, text)
    _log(event_type, message, priority, extra)
    return ok


def send_admin_alert(event_type, message, priority="warning", extra=None):
    """Send to admin alerts bot. HIGH PRIORITY ONLY."""
    emoji = PRIORITY_EMOJI.get(priority, "⚠️")
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    text = f"{emoji} <b>ADMIN ALERT</b> [{now}]\n<b>{event_type}</b>\n{message}"
    if extra:
        for k, v in list(extra.items())[:5]:
            text += f"\n• <b>{k}:</b> {v}"
    ok, _ = _send(ADMIN_TOKEN, ADMIN_CHAT_ID, text)
    _log(f"ADMIN:{event_type}", message, priority, extra)
    return ok


def send_approval_request(item):
    """
    Send formatted approval request to admin bot.
    item: dict with project, name, type, pr_url, qa_score, impact,
          confidence, workflow_source, review_id
    """
    proj = item.get("project", "yallaplays")
    name = item.get("name", "Unnamed")
    item_type = item.get("type", "game")
    pr_url = item.get("pr_url", "pending")
    qa_score = item.get("qa_score", 0)
    impact = item.get("impact", "unknown")
    confidence = item.get("confidence", 0.0)
    workflow = item.get("workflow_source", "game-factory")
    review_id = item.get("review_id", "")
    game_type = item.get("game_type", "")

    qa_emoji = "🟢" if qa_score >= 75 else ("🟡" if qa_score >= 50 else "🔴")
    eligible = qa_score >= 75

    text = f"""🎮 <b>APPROVAL REQUIRED</b>

<b>Project:</b> {proj}
<b>Type:</b> {item_type} — {game_type}
<b>Name:</b> {name}
<b>Review ID:</b> <code>{review_id}</code>

{qa_emoji} <b>QA Score:</b> {qa_score}/100 {"✅ ELIGIBLE" if eligible else "❌ BELOW THRESHOLD (75)"}
🎯 <b>AI Confidence:</b> {confidence:.0%}
📈 <b>Estimated Impact:</b> {impact}
🔧 <b>Workflow:</b> {workflow}

<b>PR:</b> {pr_url if pr_url != "pending" else "⏳ Generating..."}

{"✅ Ready for approval" if eligible else "⚠️ QA score below 75 — review before approving"}"""

    ok, _ = _send(ADMIN_TOKEN, ADMIN_CHAT_ID, text)
    _log("approval_request", f"Approval needed: {name}", "warning", {"review_id": review_id, "qa_score": qa_score})
    return ok


def notify_workflow_start(workflow_name, details=None):
    extra = {"workflow": workflow_name}
    if details:
        extra.update(details)
    return send_system_log("workflow_started", f"Workflow <b>{workflow_name}</b> started", "info", extra)


def notify_workflow_complete(workflow_name, stats=None):
    stats_str = " · ".join(f"{k}: {v}" for k, v in (stats or {}).items())
    return send_system_log("workflow_completed", f"<b>{workflow_name}</b> complete\n{stats_str}", "success", stats)


def notify_pr_created(pr_url, project, feature, extra=None):
    return send_system_log("pr_created", f"PR created for <b>{project}/{feature}</b>\n{pr_url}", "success", extra)


def notify_deployment_complete(project, feature, deployed_url=None):
    msg = f"<b>{project}/{feature}</b> deployed"
    if deployed_url:
        msg += f"\n{deployed_url}"
    return send_system_log("deploy_completed", msg, "success")


def notify_failure(error_msg, context="", priority="error"):
    return send_system_log("failure", f"<b>FAILURE</b> in {context}\n{error_msg}", priority, {"context": context})


def notify_rollback(project, reason):
    send_system_log("rollback_triggered", f"<b>ROLLBACK</b> for {project}: {reason}", "warning")
    return send_admin_alert("rollback_triggered", f"Rollback triggered for <b>{project}</b>\nReason: {reason}", "warning")


def notify_qa_failed(game_name, qa_score, issues):
    send_system_log("qa_failed", f"QA failed for <b>{game_name}</b> — score {qa_score}/100", "warning")
    return send_admin_alert("visual_qa_failed", f"<b>{game_name}</b> QA score: {qa_score}/100\nIssues: {', '.join(issues[:3])}", "warning",
                            {"game": game_name, "score": qa_score})


def notify_api_failure(api_name, error):
    send_system_log("api_failure", f"<b>{api_name} API failure</b>\n{error}", "error")
    return send_admin_alert("openai_api_failure" if "openai" in api_name.lower() else "api_failure",
                            f"<b>{api_name}</b> API failed\n{error}", "critical")


def notify_cost_report(workflow, tokens, cost_usd, games_generated=0):
    msg = f"<b>{workflow}</b> cost report\nTokens: {tokens:,} · Cost: ${cost_usd:.4f}"
    if games_generated:
        msg += f"\nGames generated: {games_generated}"
    return send_system_log("ai_cost_report", msg, "info", {"tokens": tokens, "cost_usd": f"${cost_usd:.4f}"})


def main():
    """Test Telegram connectivity."""
    print("[telegram] Testing connectivity...")
    ok1 = send_system_log("system_test", "MIFTEH OS Telegram system online ✅", "success",
                           {"version": "Phase L", "mode": "game_factory"})
    ok2 = send_admin_alert("system_test", "Admin alert bot online ✅\nGame factory active", "info")
    print(f"[telegram] System log: {'ok' if ok1 else 'failed'}, Admin alert: {'ok' if ok2 else 'failed'}")
    return ok1, ok2


if __name__ == "__main__":
    main()
