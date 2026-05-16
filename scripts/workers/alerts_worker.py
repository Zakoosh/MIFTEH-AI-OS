"""Alerts worker — reads all snapshots, computes alerts, sends Telegram."""
import json
import os
import requests
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
ALERTS_LOG = Path("memory/alerts_log.json")
OUTPUT_FILE = SNAPSHOT_DIR / "alerts_snapshot.json"
MAX_ALERTS_LOG = 200


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _send_telegram(token: str, chat_id: str, text: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception as exc:
        print(f"[alerts_worker] Telegram send failed: {exc}")


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _load_telemetry() -> dict:
    return _load_json(SNAPSHOT_DIR / "telemetry_snapshot.json")


def _load_alerts_log() -> list:
    if ALERTS_LOG.exists():
        try:
            return json.loads(ALERTS_LOG.read_text())
        except Exception:
            pass
    return []


def _save_alerts_log(log: list):
    if len(log) > MAX_ALERTS_LOG:
        log = log[-MAX_ALERTS_LOG:]
    ALERTS_LOG.write_text(json.dumps(log, indent=2))


def _format_alert(issue: dict) -> str:
    sev = issue.get("severity", "info")
    emoji = {"critical": "🔴", "warning": "🟡", "info": "ℹ️"}.get(sev, "ℹ️")
    worker = issue.get("worker", "system")
    detail = issue.get("detail", "")
    return f"{emoji} <b>[{worker}]</b> {detail}"


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    telemetry = _load_telemetry()
    all_issues = telemetry.get("all_issues", [])
    system_health = telemetry.get("system_health", "UNKNOWN")

    # Only alert on critical/warning issues
    alertable = [i for i in all_issues if i.get("severity") in ("critical", "warning")]

    log = _load_alerts_log()
    new_alerts = []

    token = os.environ.get("TELEGRAM_LOG_TOKEN")
    admin_token = os.environ.get("TELEGRAM_ADMIN_LOG_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    admin_chat = os.environ.get("TELEGRAM_ADMIN_CHAT_ID")

    if alertable and (token or admin_token):
        lines = [f"<b>🚨 MIFTEH OS — {system_health}</b>", f"<i>{_now()}</i>", ""]
        for issue in alertable[:10]:  # max 10 per batch
            lines.append(_format_alert(issue))

        if len(alertable) > 10:
            lines.append(f"... and {len(alertable)-10} more issues")

        msg = "\n".join(lines)
        if token and chat_id:
            _send_telegram(token, chat_id, msg)
        if admin_token and admin_chat:
            _send_telegram(admin_token, admin_chat, msg)

        for issue in alertable:
            entry = {**issue, "alerted_at": _now(), "system_health": system_health}
            log.append(entry)
            new_alerts.append(entry)

    _save_alerts_log(log)

    snapshot = {
        "worker": "alerts_worker",
        "timestamp": _now(),
        "system_health": system_health,
        "total_issues": len(all_issues),
        "alertable_issues": len(alertable),
        "new_alerts_sent": len(new_alerts),
        "telegram_configured": bool(token or admin_token),
        "health": "healthy" if not alertable else "warning",
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[alerts_worker] done — {len(new_alerts)} alerts sent — health={system_health}")
    return snapshot


if __name__ == "__main__":
    run()
