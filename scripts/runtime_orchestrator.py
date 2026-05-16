"""Runtime orchestrator — entry point for the autonomous MIFTEH OS runtime loop.

Runs scheduler_worker (which runs all workers), sends heartbeat, saves incident on crash.
"""
import json
import os
import sys
import traceback
import requests
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

HEARTBEAT_FILE = Path("memory/runtime_heartbeat.json")
INCIDENT_DIR   = Path("memory/incidents")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _send_telegram(text: str):
    token  = os.environ.get("TELEGRAM_LOG_TOKEN") or os.environ.get("TELEGRAM_ADMIN_LOG_TOKEN")
    chat   = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_ADMIN_CHAT_ID")
    if not token or not chat:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


def _save_heartbeat(status: str, system_health: str, detail: str = ""):
    HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    HEARTBEAT_FILE.write_text(json.dumps({
        "timestamp": _now(),
        "status": status,
        "system_health": system_health,
        "detail": detail,
    }, indent=2))


def _save_incident(exc: Exception):
    INCIDENT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    (INCIDENT_DIR / f"orchestrator_{ts}.json").write_text(json.dumps({
        "timestamp": _now(),
        "source": "runtime_orchestrator",
        "error": str(exc),
        "traceback": traceback.format_exc()[-1000:],
    }, indent=2))


def main():
    print(f"[orchestrator] starting — {_now()}")
    _send_telegram(f"🟢 <b>MIFTEH OS Runtime</b> started\n<i>{_now()}</i>")

    try:
        from workers.scheduler_worker import run as run_scheduler
        manifest = run_scheduler()

        system_health = manifest.get("health", "unknown").upper()
        ok_count      = manifest.get("ok_count", 0)
        total         = manifest.get("total_workers", 0)
        elapsed       = manifest.get("total_elapsed_sec", 0)

        _save_heartbeat("ok", system_health, f"{ok_count}/{total} workers ok")

        # Send completion heartbeat to Telegram (only on degraded/critical)
        if system_health in ("DEGRADED", "CRITICAL", "WARNING"):
            err_workers = [
                r["worker"] for r in manifest.get("results", [])
                if r.get("status") == "error"
            ]
            _send_telegram(
                f"⚠️ <b>MIFTEH OS Runtime</b> — {system_health}\n"
                f"Workers: {ok_count}/{total} ok\n"
                f"Failed: {', '.join(err_workers) or 'none'}\n"
                f"Elapsed: {elapsed}s\n"
                f"<i>{_now()}</i>"
            )
        else:
            print(f"[orchestrator] healthy — {ok_count}/{total} workers ok — {elapsed}s")

        _save_heartbeat("ok", system_health, f"completed in {elapsed}s")

    except Exception as exc:
        _save_heartbeat("error", "CRITICAL", str(exc)[:200])
        _save_incident(exc)
        _send_telegram(
            f"🔴 <b>MIFTEH OS Runtime CRASHED</b>\n"
            f"Error: {str(exc)[:300]}\n"
            f"<i>{_now()}</i>"
        )
        print(f"[orchestrator] CRASH: {exc}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
