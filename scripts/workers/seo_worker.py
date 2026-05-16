"""SEO worker — reads SEO reports, tracks coverage, detects opportunities."""
import json
from pathlib import Path
from datetime import datetime, timezone

SNAPSHOT_DIR = Path("memory/snapshots")
GAME_SEO_REPORT = Path("memory/game_seo_report.json")
PIPELINE_REPORT = Path("memory/publishing_pipeline_report.json")
OUTPUT_FILE = SNAPSHOT_DIR / "seo_snapshot.json"

MIN_SEO_COVERAGE_PCT = 60


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _count_game_dirs() -> int:
    g = Path("outputs/yallaplays/games")
    if not g.exists():
        return 0
    return len([d for d in g.iterdir() if d.is_dir()])


def run() -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    seo = _load_json(GAME_SEO_REPORT)
    pipeline = _load_json(PIPELINE_REPORT)

    total_games = _count_game_dirs()
    pages_with_seo = seo.get("pages_generated", 0)
    coverage_pct = (pages_with_seo / total_games * 100) if total_games else 0

    opportunities = []
    issues = []

    if coverage_pct < MIN_SEO_COVERAGE_PCT and total_games > 0:
        issues.append({
            "type": "low_seo_coverage",
            "severity": "warning",
            "detail": f"SEO coverage {coverage_pct:.1f}% — {pages_with_seo}/{total_games} games",
        })

    # Detect games without SEO pages
    missing_count = max(0, total_games - pages_with_seo)
    if missing_count > 0:
        opportunities.append({
            "type": "missing_seo_pages",
            "count": missing_count,
            "detail": f"{missing_count} games need SEO pages generated",
        })

    # Check sitemap freshness
    sitemap_updated = seo.get("sitemap_updated") or seo.get("generated_at")
    if not sitemap_updated:
        issues.append({
            "type": "no_sitemap",
            "severity": "info",
            "detail": "No sitemap generation recorded",
        })

    # Pipeline health
    pipeline_health = pipeline.get("overall_health", "unknown")
    if pipeline_health in ("degraded", "critical"):
        issues.append({
            "type": "pipeline_degraded",
            "severity": "warning",
            "detail": f"Publishing pipeline health: {pipeline_health}",
        })

    snapshot = {
        "worker": "seo_worker",
        "timestamp": _now(),
        "status": "ok",
        "total_games": total_games,
        "pages_with_seo": pages_with_seo,
        "coverage_pct": round(coverage_pct, 1),
        "missing_seo_pages": missing_count,
        "opportunities": opportunities,
        "issues": issues,
        "health": "warning" if issues else "healthy",
        "pipeline_health": pipeline_health,
        "sitemap_updated": sitemap_updated,
    }

    OUTPUT_FILE.write_text(json.dumps(snapshot, indent=2))
    print(f"[seo_worker] done — coverage={coverage_pct:.1f}% health={snapshot['health']}")
    return snapshot


if __name__ == "__main__":
    run()
