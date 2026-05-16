"""Weekly reporter — generates and sends the weekly Telegram report.

Runs Sunday 07:00 UTC (10:00 Istanbul). Summarizes the week's output:
games produced, pages published, indexing throughput, revenue progress,
AI provider uptime, and week-over-week deltas.
"""
import json
import os
import sys
import requests
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))

SNAPSHOT_DIR = Path("memory/snapshots")
REPORTS_DIR  = Path("memory/weekly_reports")
DAILY_REPORTS = Path("memory/daily_reports")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _week_label():
    dt = datetime.now(timezone.utc)
    start = (dt - timedelta(days=dt.weekday() + 1)).strftime("%Y-%m-%d")  # prev Sunday
    end = dt.strftime("%Y-%m-%d")
    return f"{start} → {end}"


def _load(name: str) -> dict:
    f = SNAPSHOT_DIR / name
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def _load_memory(name: str) -> dict:
    f = Path("memory") / name
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def _count_daily_reports_this_week() -> int:
    if not DAILY_REPORTS.exists():
        return 0
    dt = datetime.now(timezone.utc)
    count = 0
    for i in range(7):
        day = (dt - timedelta(days=i)).strftime("%Y-%m-%d")
        if (DAILY_REPORTS / f"{day}.txt").exists():
            count += 1
    return count


def _send_telegram(token: str, chat_id: str, text: str):
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        return resp.status_code == 200
    except Exception as exc:
        print(f"[weekly_reporter] Telegram error: {exc}")
        return False


def build_report() -> str:
    telemetry  = _load("telemetry_snapshot.json")
    games      = _load("games_snapshot.json")
    seo        = _load("seo_snapshot.json")
    indexing   = _load("indexing_snapshot.json")
    revenue    = _load("revenue_snapshot.json")
    publishing = _load("publishing_snapshot.json")
    github     = _load("github_snapshot.json")
    provider_h = _load_memory("provider_health.json")
    heartbeat  = _load_memory("runtime_heartbeat.json")

    system_health = telemetry.get("system_health", "UNKNOWN")
    health_emoji  = {
        "HEALTHY": "🟢", "WARNING": "🟡", "DEGRADED": "🟠",
        "CRITICAL": "🔴", "RECOVERING": "🔵", "UNKNOWN": "⚪"
    }.get(system_health, "⚪")

    days_reporting = _count_daily_reports_this_week()

    # Provider uptime inference
    oa_status = provider_h.get("openai", {}).get("status", "unknown")
    oa_fails  = provider_h.get("openai", {}).get("failures", 0)
    gm_status = provider_h.get("gemini", {}).get("status", "unknown")
    oa_emoji  = "🟢" if oa_status == "healthy" else "🟡"
    gm_emoji  = "🟢" if gm_status == "healthy" else "⚪"

    runtime_status = heartbeat.get("status", "unknown")
    last_heartbeat = heartbeat.get("timestamp", "N/A")

    # Issue counts
    issue_counts = telemetry.get("issue_counts", {})

    lines = [
        f"{health_emoji} <b>MIFTEH OS — Weekly Report</b>",
        f"📅 Week: {_week_label()}",
        f"System Health: <b>{system_health}</b>",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>🎮 Games This Week</b>",
        f"  Total Games: {games.get('total_games', 0)}/{games.get('target_games', 30)} ({games.get('progress_pct', 0)}%)",
        f"  QA Passed: {games.get('qa_passed', 0)} | Failed: {games.get('qa_failed', 0)}",
        f"  Avg QA Score: {games.get('avg_qa_score', 0)}/100",
        f"  Factory Errors: {games.get('factory_errors', 0)}",
        "",
        "<b>🚀 Publishing</b>",
        f"  Deployed: {publishing.get('deployed_count', 0)}",
        f"  Pending Approval: {publishing.get('pending_approval', 0)}",
        f"  QA Blocked: {publishing.get('blocked_by_qa', 0)}",
        f"  Pipeline Completion: {publishing.get('completion_rate_pct', 0)}%",
        "",
        "<b>🔍 SEO & Indexing</b>",
        f"  Games with SEO: {seo.get('pages_with_seo', 0)} ({seo.get('coverage_pct', 0)}%)",
        f"  Missing SEO: {seo.get('missing_seo_pages', 0)}",
        f"  Indexing Queue: {indexing.get('queue_size', 0)}",
        f"  Failed URLs: {indexing.get('failed_count', 0)}",
        f"  Total Indexed: {indexing.get('total_submitted', 0)}",
        "",
        "<b>💰 Revenue</b>",
        f"  MRR: ${revenue.get('mrr_usd', 0):.2f}",
        f"  Target: ${revenue.get('mrr_target_usd', 500)}",
        f"  Stage: {revenue.get('revenue_stage', 'pre-revenue')}",
        f"  Avg RPM: ${revenue.get('avg_rpm_usd', 0):.2f}",
        "",
        "<b>⚙️ AI Providers</b>",
        f"  {oa_emoji} OpenAI: {oa_status} ({oa_fails} failures)",
        f"  {gm_emoji} Gemini: {gm_status}",
        "",
        "<b>🔧 GitHub Actions</b>",
        f"  Healthy: {github.get('healthy_count', 0)}/{github.get('tracked_workflows', 0)}",
        f"  Failed: {github.get('failed_count', 0)}",
        f"  Missing: {github.get('missing_count', 0)}",
        "",
        "<b>⚡ Runtime</b>",
        f"  Status: {runtime_status}",
        f"  Last heartbeat: {last_heartbeat}",
        f"  Daily reports sent: {days_reporting}/7",
        f"  Total issues: {telemetry.get('total_issues', 0)}",
        f"  Critical: {issue_counts.get('critical', 0)} | Warning: {issue_counts.get('warning', 0)}",
        "",
        f"<i>Generated {_now()}</i>",
    ]

    return "\n".join(lines)


def run():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report_text = build_report()
    dt = datetime.now(timezone.utc)
    week_key = f"{dt.strftime('%Y')}-W{dt.strftime('%W')}"

    (REPORTS_DIR / f"{week_key}.txt").write_text(report_text)

    print(report_text)

    token      = os.environ.get("TELEGRAM_LOG_TOKEN")
    admin_tok  = os.environ.get("TELEGRAM_ADMIN_LOG_TOKEN")
    chat_id    = os.environ.get("TELEGRAM_CHAT_ID")
    admin_chat = os.environ.get("TELEGRAM_ADMIN_CHAT_ID")

    sent = False
    if token and chat_id:
        sent = _send_telegram(token, chat_id, report_text)
    if admin_tok and admin_chat:
        _send_telegram(admin_tok, admin_chat, report_text)

    result = {
        "week": week_key,
        "sent": sent,
        "telegram_configured": bool(token or admin_tok),
        "char_count": len(report_text),
    }
    (REPORTS_DIR / f"{week_key}_meta.json").write_text(json.dumps(result, indent=2))
    print(f"[weekly_reporter] done — sent={sent}")
    return result


if __name__ == "__main__":
    run()
