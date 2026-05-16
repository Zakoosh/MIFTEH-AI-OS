"""Weekly reporter — generates and sends the weekly Telegram report.

Runs Sunday 07:00 UTC (10:00 Istanbul). Includes all 13 focus mode report fields
with week-over-week deltas and full runtime summary.
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
    start = (dt - timedelta(days=dt.weekday() + 1)).strftime("%Y-%m-%d")
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


def _load_list(name: str) -> list:
    f = Path("memory") / name
    if f.exists():
        try:
            data = json.loads(f.read_text())
            return data if isinstance(data, list) else []
        except Exception:
            pass
    return []


def _count_daily_reports_this_week() -> int:
    if not DAILY_REPORTS.exists():
        return 0
    dt = datetime.now(timezone.utc)
    return sum(
        1 for i in range(7)
        if (DAILY_REPORTS / f"{(dt - timedelta(days=i)).strftime('%Y-%m-%d')}.txt").exists()
    )


def _send_telegram(token: str, chat_id: str, text: str) -> bool:
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


def _week_targets_summary(history: list) -> dict:
    """Aggregate this week's daily target records."""
    dt = datetime.now(timezone.utc)
    week_dates = {(dt - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)}
    week_records = [h for h in history if h.get("date") in week_dates]
    if not week_records:
        return {}
    return {
        "total_games": sum(r.get("games", 0) for r in week_records),
        "total_seo_pages": sum(r.get("seo_pages", 0) for r in week_records),
        "total_indexing": sum(r.get("indexing_growth", 0) for r in week_records),
        "avg_qa": round(sum(r.get("qa_avg", 0) for r in week_records) / len(week_records), 1),
        "days_all_targets_met": sum(1 for r in week_records if r.get("all_met")),
        "days_tracked": len(week_records),
    }


def build_report() -> str:
    telemetry  = _load("telemetry_snapshot.json")
    games      = _load("games_snapshot.json")
    seo        = _load("seo_snapshot.json")
    indexing   = _load("indexing_snapshot.json")
    revenue    = _load("revenue_snapshot.json")
    publishing = _load("publishing_snapshot.json")
    github     = _load("github_snapshot.json")
    learning   = _load("learning_snapshot.json")
    provider_h = _load_memory("provider_health.json")
    heartbeat  = _load_memory("runtime_heartbeat.json")
    governance = _load_memory("admin_governance_report.json")
    pipeline   = _load_memory("publishing_pipeline_report.json")
    focus      = _load_memory("focus_mode.json")
    target_hist = _load_list("target_history.json")

    system_health = telemetry.get("system_health", "UNKNOWN")
    health_emoji  = {
        "HEALTHY": "🟢", "WARNING": "🟡", "DEGRADED": "🟠",
        "CRITICAL": "🔴", "RECOVERING": "🔵", "UNKNOWN": "⚪"
    }.get(system_health, "⚪")

    days_reporting = _count_daily_reports_this_week()
    week_targets = _week_targets_summary(target_hist)

    # ── 13 required fields (weekly totals) ───────────────────────────────────
    gov_counts = governance.get("counts", {})
    games_approved = gov_counts.get("approved", 0) + gov_counts.get("deployed", 0)
    games_blocked  = gov_counts.get("rejected", 0) + gov_counts.get("qa_failed", 0)

    # CTR estimates from pipeline
    pipeline_games = pipeline.get("games", [])
    ctr_raw = [g.get("ctr_estimate", "").replace("%", "").strip() for g in pipeline_games if g.get("ctr_estimate")]
    try:
        avg_ctr = sum(float(c) for c in ctr_raw if c) / max(len(ctr_raw), 1)
    except Exception:
        avg_ctr = 0

    # RPM
    avg_rpm = learning.get("avg_rpm", 0)
    mrr = revenue.get("mrr_usd", 0)

    # Top categories
    qa_by_type = learning.get("qa", {}).get("by_type", {})
    top_cats = sorted(qa_by_type.items(), key=lambda x: x[1], reverse=True)[:3] if qa_by_type else []

    # Trends (from learning)
    trends = learning.get("trends", [])
    recommendations = _load_memory("learning_insights.json").get("recommendations", [])

    # Provider health
    oa_status = provider_h.get("openai", {}).get("status", "unknown")
    oa_fails  = provider_h.get("openai", {}).get("failures", 0)
    gm_status = provider_h.get("gemini", {}).get("status", "unknown")
    oa_emoji  = "🟢" if oa_status == "healthy" else "🟡"
    gm_emoji  = "🟢" if gm_status == "healthy" else "⚪"

    focus_mode = focus.get("label", "YallaPlays Focus Mode")
    focus_expires = focus.get("expires_at", "")[:10] if focus.get("expires_at") else ""
    issue_counts = telemetry.get("issue_counts", {})

    lines = [
        f"{health_emoji} <b>MIFTEH OS — Weekly Report</b>",
        f"📅 Week: {_week_label()}",
        f"{focus_mode} | Expires: {focus_expires}",
        f"System: <b>{system_health}</b>",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>🎯 Weekly Targets Summary</b>",
        f"  Days tracked: {week_targets.get('days_tracked', 0)}/7",
        f"  Days all targets met: {week_targets.get('days_all_targets_met', 0)}",
        f"  Total games generated: {week_targets.get('total_games', 0)}",
        f"  Total SEO pages: {week_targets.get('total_seo_pages', 0)}",
        f"  Total indexed: {week_targets.get('total_indexing', 0)}",
        f"  Avg QA score: {week_targets.get('avg_qa', 0)}/100",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>🎮 Games (Week)</b>",
        f"  1️⃣  Generated: {week_targets.get('total_games', games.get('total_games', 0))}",
        f"  2️⃣  Approved: {games_approved}",
        f"  3️⃣  Blocked: {games_blocked}",
        f"  Total in platform: {games.get('total_games', 0)}/{games.get('target_games', 30)}",
        f"  Factory errors: {games.get('factory_errors', 0)}",
        "",
        "<b>🔍 SEO & Indexing (Week)</b>",
        f"  4️⃣  Indexing Growth: +{week_targets.get('total_indexing', 0)} URLs",
        f"       Total indexed all time: {indexing.get('total_submitted', 0)}",
        f"  5️⃣  SEO Pages: {seo.get('pages_with_seo', 0)} ({seo.get('coverage_pct', 0)}% coverage)",
        f"       Missing: {seo.get('missing_seo_pages', 0)} games",
        f"  9️⃣  QA Avg: {week_targets.get('avg_qa', 0)}/100",
    ]

    if top_cats:
        lines.append("")
        lines.append("<b>7️⃣  Top Performing Categories</b>")
        for cat, score in top_cats:
            lines.append(f"  🏆 {cat}: {score}/100 avg QA")

    if trends:
        lines.append("")
        lines.append("<b>8️⃣  Detected Trends</b>")
        for t in trends[:5]:
            lines.append(f"  📈 {t.get('detail', '')[:80]}")

    lines += [
        "",
        "<b>🚀 Deployment</b>",
        f"  🔟 Deploy Rate: {publishing.get('completion_rate_pct', 0)}%",
        f"       Deployed: {publishing.get('deployed_count', 0)} | Pending: {publishing.get('pending_approval', 0)}",
        "",
        "<b>💰 Revenue</b>",
        f"  6️⃣  MRR: ${mrr:.2f} | Stage: {revenue.get('revenue_stage', 'pre-revenue')}",
        f"  1️⃣1️⃣ CTR Est: {avg_ctr:.1f}% avg",
        f"  1️⃣2️⃣ RPM: ${avg_rpm:.2f} (target $0.80–$3.50)",
        "",
        "<b>⚙️ AI Providers</b>",
        f"  {oa_emoji} OpenAI: {oa_status} ({oa_fails} failures this week)",
        f"  {gm_emoji} Gemini: {gm_status}",
        "",
        "<b>🔧 GitHub Actions</b>",
        f"  Healthy: {github.get('healthy_count', 0)}/{github.get('tracked_workflows', 0)}",
        f"  Failed: {github.get('failed_count', 0)} | Missing: {github.get('missing_count', 0)}",
        "",
        "<b>⚡ Runtime</b>",
        f"  Status: {heartbeat.get('status', 'unknown')}",
        f"  Daily reports sent: {days_reporting}/7",
        f"  Total issues: {telemetry.get('total_issues', 0)}",
        f"  Critical: {issue_counts.get('critical', 0)} | Warning: {issue_counts.get('warning', 0)}",
    ]

    if recommendations:
        lines.append("")
        lines.append("<b>💡 AI Recommendations</b>")
        for r in recommendations[:3]:
            lines.append(f"  → {r.get('action', '')[:80]}")

    lines.append("")
    lines.append(f"<i>Generated {_now()}</i>")
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
