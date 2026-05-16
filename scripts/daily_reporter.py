"""Daily reporter — generates and sends the daily Telegram report.

Runs at 06:00 UTC (09:00 Istanbul). Reads all snapshot files and sends
a formatted HTML summary covering: system health, games, SEO, indexing,
revenue, providers, and open issues.
"""
import json
import os
import sys
import requests
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

SNAPSHOT_DIR = Path("memory/snapshots")
REPORTS_DIR  = Path("memory/daily_reports")


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


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


def _send_telegram(token: str, chat_id: str, text: str):
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
        return resp.status_code == 200
    except Exception as exc:
        print(f"[daily_reporter] Telegram error: {exc}")
        return False


def build_report() -> str:
    telemetry   = _load("telemetry_snapshot.json")
    analytics   = _load("analytics_snapshot.json")
    games       = _load("games_snapshot.json")
    seo         = _load("seo_snapshot.json")
    indexing    = _load("indexing_snapshot.json")
    revenue     = _load("revenue_snapshot.json")
    publishing  = _load("publishing_snapshot.json")
    github      = _load("github_snapshot.json")
    provider_h  = _load_memory("provider_health.json")

    system_health = telemetry.get("system_health", "UNKNOWN")
    health_emoji = {
        "HEALTHY": "🟢", "WARNING": "🟡", "DEGRADED": "🟠",
        "CRITICAL": "🔴", "RECOVERING": "🔵", "UNKNOWN": "⚪"
    }.get(system_health, "⚪")

    # Format providers
    oa_status = provider_h.get("openai", {}).get("status", "unknown")
    gm_status = provider_h.get("gemini", {}).get("status", "unknown")
    oa_emoji  = "🟢" if oa_status == "healthy" else "🔴"
    gm_emoji  = "🟢" if gm_status == "healthy" else "⚪"

    lines = [
        f"{health_emoji} <b>MIFTEH OS — Daily Report</b>",
        f"📅 {_today()} | System: <b>{system_health}</b>",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>🎮 Games</b>",
        f"  Total: {games.get('total_games', 0)}/{games.get('target_games', 30)}",
        f"  QA Pass: {games.get('qa_passed', 0)}/{games.get('qa_total', 0)} ({games.get('qa_pass_rate_pct', 0)}%)",
        f"  Avg Score: {games.get('avg_qa_score', 0)}/100",
        "",
        "<b>🚀 Publishing</b>",
        f"  Deployed: {publishing.get('deployed_count', 0)}",
        f"  Pending Approval: {publishing.get('pending_approval', 0)}",
        f"  Pipeline Complete: {publishing.get('completion_rate_pct', 0)}%",
        "",
        "<b>🔍 SEO & Indexing</b>",
        f"  SEO Coverage: {seo.get('coverage_pct', 0)}% ({seo.get('pages_with_seo', 0)} pages)",
        f"  Queue: {indexing.get('queue_size', 0)} | Failed: {indexing.get('failed_count', 0)}",
        f"  Today Submitted: {indexing.get('submitted_today', 0)}/200",
        f"  Quota Remaining: {indexing.get('quota_remaining', 200)}",
        "",
        "<b>💰 Revenue</b>",
        f"  MRR: ${revenue.get('mrr_usd', 0):.2f} (target ${revenue.get('mrr_target_usd', 500)})",
        f"  Stage: {revenue.get('revenue_stage', 'pre-revenue')}",
        "",
        "<b>⚙️ AI Providers</b>",
        f"  {oa_emoji} OpenAI: {oa_status}",
        f"  {gm_emoji} Gemini: {gm_status}",
        "",
        "<b>🔧 GitHub Actions</b>",
        f"  Healthy: {github.get('healthy_count', 0)} | Failed: {github.get('failed_count', 0)}",
    ]

    # Issues section
    all_issues = telemetry.get("all_issues", [])
    critical_issues = [i for i in all_issues if i.get("severity") == "critical"]
    warning_issues  = [i for i in all_issues if i.get("severity") == "warning"]

    if critical_issues or warning_issues:
        lines.append("")
        lines.append("<b>⚠️ Open Issues</b>")
        for issue in (critical_issues + warning_issues)[:5]:
            sev_emoji = "🔴" if issue.get("severity") == "critical" else "🟡"
            lines.append(f"  {sev_emoji} {issue.get('detail', '')[:80]}")
        if len(all_issues) > 5:
            lines.append(f"  ... and {len(all_issues)-5} more")

    lines.append("")
    lines.append(f"<i>Generated {_now()}</i>")

    return "\n".join(lines)


def run():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report_text = build_report()
    today = _today()

    # Save report locally
    (REPORTS_DIR / f"{today}.txt").write_text(report_text)

    print(report_text)

    # Send to Telegram
    token     = os.environ.get("TELEGRAM_LOG_TOKEN")
    admin_tok = os.environ.get("TELEGRAM_ADMIN_LOG_TOKEN")
    chat_id   = os.environ.get("TELEGRAM_CHAT_ID")
    admin_chat = os.environ.get("TELEGRAM_ADMIN_CHAT_ID")

    sent = False
    if token and chat_id:
        sent = _send_telegram(token, chat_id, report_text)
    if admin_tok and admin_chat:
        _send_telegram(admin_tok, admin_chat, report_text)

    result = {
        "date": today,
        "sent": sent,
        "telegram_configured": bool(token or admin_tok),
        "char_count": len(report_text),
    }
    (REPORTS_DIR / f"{today}_meta.json").write_text(json.dumps(result, indent=2))
    print(f"[daily_reporter] done — sent={sent}")
    return result


if __name__ == "__main__":
    run()
