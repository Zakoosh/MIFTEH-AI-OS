"""Target tracker — measures daily targets against focus mode minimums.

Daily targets (from focus_mode.py):
- 5+ playable games/day
- 20+ SEO pages/day
- 95% mobile compatibility
- QA score > 80
- indexed URLs growth daily
- new keyword discovery daily
"""
import json
from datetime import datetime, timezone
from pathlib import Path

SNAPSHOT_DIR = Path("memory/snapshots")
OUTPUT_FILE = SNAPSHOT_DIR / "target_tracker_snapshot.json"
HISTORY_FILE = Path("memory/target_history.json")
MAX_HISTORY = 14  # 2 weeks


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _games_today() -> int:
    """Count games generated today."""
    factory = _load_json(Path("memory/game_factory_report.json"))
    gen_at = factory.get("generated_at", "")
    if gen_at.startswith(_today()):
        return factory.get("games_generated", 0)
    return 0


def _seo_pages_today() -> int:
    """Count SEO pages generated today."""
    seo = _load_json(Path("memory/game_seo_report.json"))
    gen_at = seo.get("generated_at", "")
    if gen_at.startswith(_today()):
        return seo.get("seo_pages_count", 0)
    return 0


def _qa_avg_today() -> float:
    """Average QA score from today's factory run."""
    factory = _load_json(Path("memory/game_factory_report.json"))
    gen_at = factory.get("generated_at", "")
    if gen_at.startswith(_today()):
        return factory.get("avg_qa_score", 0)
    return 0


def _mobile_compat_pct() -> float:
    """Mobile compatibility — from QA summary."""
    qa = _load_json(Path("memory/game_qa_report.json"))
    summary = qa.get("summary", {})
    total = summary.get("total", 0)
    if total == 0:
        return 0.0
    games = qa.get("games", [])
    mobile_ok = sum(1 for g in games if g.get("qa_score", 0) >= 75)
    return round(mobile_ok / total * 100, 1) if total else 0.0


def _indexing_growth_today() -> int:
    """URLs indexed today."""
    report = _load_json(Path("memory/indexing_report.json"))
    return report.get("indexed_today", 0)


def _keywords_today() -> int:
    """New keywords discovered — from SEO report."""
    seo = _load_json(Path("memory/game_seo_report.json"))
    gen_at = seo.get("generated_at", "")
    if gen_at.startswith(_today()):
        return seo.get("total_keywords", 0)
    return 0


def _load_focus_targets() -> dict:
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from focus_mode import get_daily_targets
        return get_daily_targets()
    except Exception:
        return {
            "games_generated_min": 5,
            "seo_pages_min": 20,
            "mobile_compatibility_pct": 95,
            "qa_score_min": 80,
            "indexed_urls_growth": True,
            "new_keywords_daily": True,
        }


def _check_target(value, minimum, label: str) -> dict:
    met = value >= minimum if isinstance(minimum, (int, float)) else bool(value)
    return {
        "label": label,
        "target": minimum,
        "actual": value,
        "met": met,
        "gap": max(0, minimum - value) if isinstance(minimum, (int, float)) else 0,
    }


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    targets = _load_focus_targets()

    games_today = _games_today()
    seo_today = _seo_pages_today()
    qa_avg = _qa_avg_today()
    mobile_pct = _mobile_compat_pct()
    indexing_growth = _indexing_growth_today()
    keywords_today = _keywords_today()

    checks = [
        _check_target(games_today, targets.get("games_generated_min", 5), "Games Generated"),
        _check_target(seo_today, targets.get("seo_pages_min", 20), "SEO Pages"),
        _check_target(qa_avg, targets.get("qa_score_min", 80), "Avg QA Score"),
        _check_target(mobile_pct, targets.get("mobile_compatibility_pct", 95), "Mobile Compat %"),
        _check_target(indexing_growth, 1, "Indexing Growth"),
        _check_target(keywords_today, 1, "New Keywords"),
    ]

    met_count = sum(1 for c in checks if c["met"])
    total_count = len(checks)
    all_met = met_count == total_count
    health = "healthy" if all_met else ("warning" if met_count >= total_count // 2 else "critical")

    issues = []
    for c in checks:
        if not c["met"]:
            issues.append({
                "type": "target_missed",
                "severity": "warning",
                "detail": f"{c['label']}: {c['actual']} / target {c['target']} (gap: {c['gap']})",
            })

    # Persist daily history
    history = []
    if HISTORY_FILE.exists():
        try:
            history = json.loads(HISTORY_FILE.read_text())
        except Exception:
            pass

    today_record = {
        "date": _today(),
        "games": games_today,
        "seo_pages": seo_today,
        "qa_avg": qa_avg,
        "mobile_pct": mobile_pct,
        "indexing_growth": indexing_growth,
        "keywords": keywords_today,
        "targets_met": met_count,
        "targets_total": total_count,
        "all_met": all_met,
    }

    # Replace today's record if exists
    history = [h for h in history if h.get("date") != _today()]
    history.append(today_record)
    history = history[-MAX_HISTORY:]
    HISTORY_FILE.write_text(json.dumps(history, indent=2))

    snapshot = {
        "worker": "target_tracker",
        "timestamp": _now(),
        "date": _today(),
        "status": "ok",
        "targets_met": met_count,
        "targets_total": total_count,
        "all_targets_met": all_met,
        "checks": checks,
        "today": today_record,
        "history": history,
        "issues": issues,
        "health": health,
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[target_tracker] done — {met_count}/{total_count} targets met — health={health}")
    return snapshot


if __name__ == "__main__":
    run()
