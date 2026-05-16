"""Daily reporter — generates and sends the daily Telegram report.

Runs at 06:00 UTC (09:00 Istanbul). Includes all 13 focus mode report fields:
games_generated, games_approved, games_blocked, indexing_growth, seo_growth,
estimated_revenue_impact, top_performing_categories, detected_trends,
qa_averages, deployment_success_rate, estimated_ctr_growth, estimated_rpm_growth.
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


def _send_telegram(token: str, chat_id: str, text: str) -> bool:
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


def _pct(value, target) -> str:
    if target <= 0:
        return "N/A"
    p = value / target * 100
    return f"{p:.0f}%"


def build_report() -> str:
    telemetry    = _load("telemetry_snapshot.json")
    analytics    = _load("analytics_snapshot.json")
    games        = _load("games_snapshot.json")
    seo          = _load("seo_snapshot.json")
    indexing     = _load("indexing_snapshot.json")
    revenue      = _load("revenue_snapshot.json")
    publishing   = _load("publishing_snapshot.json")
    github       = _load("github_snapshot.json")
    learning     = _load("learning_snapshot.json")
    targets      = _load("target_tracker_snapshot.json")
    provider_h   = _load_memory("provider_health.json")
    factory      = _load_memory("game_factory_report.json")
    qa_report    = _load_memory("game_qa_report.json")
    governance   = _load_memory("admin_governance_report.json")
    pipeline     = _load_memory("publishing_pipeline_report.json")
    focus        = _load_memory("focus_mode.json")

    system_health = telemetry.get("system_health", "UNKNOWN")
    health_emoji = {
        "HEALTHY": "🟢", "WARNING": "🟡", "DEGRADED": "🟠",
        "CRITICAL": "🔴", "RECOVERING": "🔵", "UNKNOWN": "⚪"
    }.get(system_health, "⚪")

    # ── 13 required fields ────────────────────────────────────────────────────
    # 1. games_generated
    games_gen = factory.get("games_generated", 0)
    # 2. games_approved
    gov_counts = governance.get("counts", {})
    games_approved = gov_counts.get("approved", 0) + gov_counts.get("deployed", 0)
    # 3. games_blocked
    games_blocked = gov_counts.get("rejected", 0) + gov_counts.get("qa_failed", 0)
    # 4. indexing_growth
    indexing_growth = indexing.get("submitted_today", 0)
    # 5. seo_growth
    seo_growth = seo.get("pages_with_seo", 0)
    # 6. estimated_revenue_impact
    mrr = revenue.get("mrr_usd", 0)
    rpm = learning.get("avg_rpm", 0)
    # 7. top_performing_categories
    qa_by_type = learning.get("qa", {}).get("by_type", {})
    top_cats = sorted(qa_by_type.items(), key=lambda x: x[1], reverse=True)[:3] if qa_by_type else []
    # 8. detected_trends
    trends = learning.get("trends", []) or _load("learning_snapshot.json").get("trends", [])
    # 9. qa_averages
    qa_avg = games.get("avg_qa_score", 0) or factory.get("avg_qa_score", 0)
    qa_pass_rate = games.get("qa_pass_rate_pct", 0)
    # 10. deployment_success_rate
    deploy_rate = publishing.get("completion_rate_pct", 0)
    deployed = publishing.get("deployed_count", 0)
    # 11. estimated_ctr_growth
    pipeline_games = pipeline.get("games", [])
    ctr_estimates = [g.get("ctr_estimate", "").replace("%", "").strip() for g in pipeline_games if g.get("ctr_estimate")]
    try:
        ctr_vals = [float(c) for c in ctr_estimates if c]
        avg_ctr = sum(ctr_vals) / len(ctr_vals) if ctr_vals else 0
    except Exception:
        avg_ctr = 0
    # 12. estimated_rpm_growth
    avg_rpm = learning.get("avg_rpm", 0)

    # ── Targets status ────────────────────────────────────────────────────────
    target_checks = targets.get("checks", [])
    targets_met = targets.get("targets_met", 0)
    targets_total = targets.get("targets_total", 0)

    # ── Providers ─────────────────────────────────────────────────────────────
    oa_status = provider_h.get("openai", {}).get("status", "unknown")
    gm_status = provider_h.get("gemini", {}).get("status", "unknown")
    oa_emoji = "🟢" if oa_status == "healthy" else "🔴"
    gm_emoji = "🟢" if gm_status == "healthy" else "⚪"

    # ── Focus mode ────────────────────────────────────────────────────────────
    focus_mode = focus.get("label", "YallaPlays Focus Mode")
    focus_expires = focus.get("expires_at", "")[:10] if focus.get("expires_at") else ""

    lines = [
        f"{health_emoji} <b>MIFTEH OS — Daily Report</b>",
        f"📅 {_today()} | {focus_mode}",
        f"System: <b>{system_health}</b> | Expires: {focus_expires}",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>🎯 Daily Targets</b>",
        f"  Met: {targets_met}/{targets_total} {'✅' if targets_met == targets_total else '⚠️'}",
    ]
    for c in target_checks:
        icon = "✅" if c.get("met") else "❌"
        lines.append(f"  {icon} {c.get('label')}: {c.get('actual')} / {c.get('target')}")

    lines += [
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "<b>🎮 Games</b>",
        f"  1️⃣  Generated: {games_gen}",
        f"  2️⃣  Approved: {games_approved}",
        f"  3️⃣  Blocked: {games_blocked}",
        f"  9️⃣  QA Avg: {qa_avg}/100 ({qa_pass_rate}% pass rate)",
        "",
        "<b>🔍 SEO & Indexing</b>",
        f"  4️⃣  Indexing Growth: +{indexing_growth} URLs today",
        f"  5️⃣  SEO Pages: {seo_growth} total ({seo.get('coverage_pct', 0)}% coverage)",
        f"  Missing SEO: {seo.get('missing_seo_pages', 0)} games",
    ]

    if top_cats:
        lines.append("")
        lines.append("<b>7️⃣  Top Categories</b>")
        for cat, score in top_cats:
            lines.append(f"  🏆 {cat}: {score}/100 avg QA")

    if trends:
        lines.append("")
        lines.append("<b>8️⃣  Detected Trends</b>")
        for t in trends[:4]:
            lines.append(f"  📈 {t.get('detail', '')[:80]}")

    lines += [
        "",
        "<b>🚀 Deployment</b>",
        f"  🔟 Deploy Rate: {deploy_rate}% ({deployed} deployed)",
        "",
        "<b>💰 Revenue</b>",
        f"  6️⃣  MRR: ${mrr:.2f} | Est Impact: ${mrr * 1.05:.2f} (+5% projected)",
        f"  1️⃣1️⃣ CTR Est: {avg_ctr:.1f}% avg",
        f"  1️⃣2️⃣ RPM: ${avg_rpm:.2f}",
        "",
        "<b>⚙️ AI Providers</b>",
        f"  {oa_emoji} OpenAI: {oa_status}",
        f"  {gm_emoji} Gemini: {gm_status}",
        "",
        "<b>🔧 GitHub Actions</b>",
        f"  Healthy: {github.get('healthy_count', 0)} | Failed: {github.get('failed_count', 0)}",
    ]

    # Issues
    all_issues = telemetry.get("all_issues", [])
    critical = [i for i in all_issues if i.get("severity") == "critical"]
    warnings = [i for i in all_issues if i.get("severity") == "warning"]
    if critical or warnings:
        lines.append("")
        lines.append("<b>⚠️ Open Issues</b>")
        for i in (critical + warnings)[:5]:
            lines.append(f"  {'🔴' if i.get('severity') == 'critical' else '🟡'} {i.get('detail', '')[:80]}")

    lines.append("")
    lines.append(f"<i>Generated {_now()}</i>")
    return "\n".join(lines)


def run():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_text = build_report()
    today = _today()
    (REPORTS_DIR / f"{today}.txt").write_text(report_text)

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
