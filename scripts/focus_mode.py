"""Focus Mode Configuration for MIFTEH OS runtime.

Defines the 7-day YallaPlays priority allocation and daily targets.
Persisted in memory/focus_mode.json — read by all workers and reporters.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

FOCUS_FILE = Path("memory/focus_mode.json")

DEFAULT_FOCUS = {
    "mode": "yallaplays_priority",
    "label": "YallaPlays 7-Day Focus Mode",
    "activated_at": None,
    "expires_at": None,
    "allocation": {
        "yallaplays": 80,
        "mifteh": 15,
        "fionera": 5,
    },
    "game_priority_order": [
        "racing",
        "drift",
        "idle",
        "clicker",
        "puzzle",
        "kids",
        "reaction",
        "runner",
        "car",
        "action",
        "survival",
        "brain",
    ],
    "daily_targets": {
        "games_generated_min": 5,
        "seo_pages_min": 20,
        "mobile_compatibility_pct": 95,
        "qa_score_min": 80,
        "indexed_urls_growth": True,
        "new_keywords_daily": True,
        "ctr_improvement_weekly": True,
    },
    "pinned_dashboard_tabs": [
        "game-factory",
        "generated-games",
        "game-qa",
        "publishing-pipeline",
        "indexing-status",
        "revenue-tracker",
        "runtime-health",
    ],
    "auto_hide_empty_sections": True,
    "learning_inputs": [
        "qa_pass_rates",
        "indexing_success_failure",
        "ctr_estimates",
        "session_duration",
        "bounce_rate",
        "trend_signals",
        "approval_history",
        "deployment_success",
        "ranking_improvements",
        "revenue_performance",
    ],
    "reporting_fields": [
        "games_generated",
        "games_approved",
        "games_blocked",
        "indexing_growth",
        "seo_growth",
        "estimated_revenue_impact",
        "top_performing_categories",
        "detected_trends",
        "qa_averages",
        "deployment_success_rate",
        "estimated_ctr_growth",
        "estimated_rpm_growth",
    ],
}


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load() -> dict:
    """Load focus mode config from disk, returning defaults if missing."""
    if FOCUS_FILE.exists():
        try:
            return json.loads(FOCUS_FILE.read_text())
        except Exception:
            pass
    return dict(DEFAULT_FOCUS)


def save(config: dict):
    FOCUS_FILE.parent.mkdir(parents=True, exist_ok=True)
    config["updated_at"] = _now()
    FOCUS_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False))


def activate(days: int = 7):
    """Activate focus mode for N days, writing to disk."""
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    config = dict(DEFAULT_FOCUS)
    config["activated_at"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    config["expires_at"] = (now + timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    config["active"] = True
    save(config)
    print(f"[focus_mode] Activated — expires {config['expires_at']}")
    return config


def is_active() -> bool:
    cfg = load()
    if not cfg.get("active"):
        return True  # always active if no explicit deactivation
    expires = cfg.get("expires_at")
    if not expires:
        return True
    try:
        exp_dt = datetime.fromisoformat(expires.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) < exp_dt
    except Exception:
        return True


def get_game_priority_order() -> list:
    return load().get("game_priority_order", DEFAULT_FOCUS["game_priority_order"])


def get_daily_targets() -> dict:
    return load().get("daily_targets", DEFAULT_FOCUS["daily_targets"])


def get_allocation() -> dict:
    return load().get("allocation", DEFAULT_FOCUS["allocation"])


def get_pinned_tabs() -> list:
    return load().get("pinned_dashboard_tabs", DEFAULT_FOCUS["pinned_dashboard_tabs"])


if __name__ == "__main__":
    cfg = activate(7)
    print(json.dumps(cfg, indent=2))
