"""
safety_limits.py — Hard safety limits for the Autonomous Operational Loops Layer.

These limits are non-negotiable and cannot be overridden by config or API.
They represent the absolute ceiling on autonomous behavior.
"""

from __future__ import annotations

from pathlib import Path
import json
from datetime import datetime, date


# ---------------------------------------------------------------------------
# Absolute hard limits (cannot be lowered by config)
# ---------------------------------------------------------------------------

HARD_MAX_PER_CYCLE: int = 5          # Never apply more than 5 per cycle
HARD_MAX_PER_DAY: int = 20           # Never apply more than 20 per day
HARD_MIN_TRUST: float = 50.0         # Never auto-apply below this trust score
HARD_MAX_ROLLBACK_RATE: float = 30.0 # Always suspend if rollback rate exceeds this

# Allowed operation types for autonomous apply (subset of apply layer's whitelist)
AUTONOMOUS_ALLOWED_TYPES: set[str] = {
    "seo",
    "metadata",
    "manifest",
    "landing_page",
    "category",
    "dashboard",
    "widget",
    "watchlist",
}

# Operations that require human review regardless of trust score
ALWAYS_HUMAN_REVIEW: set[str] = {
    "auth",
    "payment",
    "database",
    "migration",
    "credentials",
    "deployment",
}

# Storage for daily counter
_DAILY_COUNTER_PATH = Path("app/memory/autonomy/config/daily_counts.json")


# ---------------------------------------------------------------------------
# Daily cap enforcement
# ---------------------------------------------------------------------------

def _load_daily_counts() -> dict:
    """Load the daily apply count file."""
    _DAILY_COUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not _DAILY_COUNTER_PATH.exists():
        return {}
    try:
        return json.loads(_DAILY_COUNTER_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_daily_counts(counts: dict) -> None:
    _DAILY_COUNTER_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        _DAILY_COUNTER_PATH.write_text(
            json.dumps(counts, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def get_today_count() -> int:
    """Return number of autonomous applies executed today."""
    today = str(date.today())
    counts = _load_daily_counts()
    return counts.get(today, 0)


def increment_today_count(amount: int = 1) -> int:
    """Increment and persist today's apply count. Returns new count."""
    today = str(date.today())
    counts = _load_daily_counts()
    counts[today] = counts.get(today, 0) + amount
    _save_daily_counts(counts)
    return counts[today]


def reset_today_count() -> None:
    """Reset today's count (e.g., for testing)."""
    today = str(date.today())
    counts = _load_daily_counts()
    counts[today] = 0
    _save_daily_counts(counts)


def is_daily_cap_reached(max_per_day: int) -> tuple[bool, int, int]:
    """Check if the daily apply cap has been reached.

    Returns (cap_reached, current_count, effective_limit).
    effective_limit = min(max_per_day, HARD_MAX_PER_DAY).
    """
    limit = min(max_per_day, HARD_MAX_PER_DAY)
    count = get_today_count()
    return count >= limit, count, limit


# ---------------------------------------------------------------------------
# Operation type guards
# ---------------------------------------------------------------------------

def is_autonomous_allowed_type(operation_type: str) -> bool:
    """Return True if the operation type may be run autonomously."""
    return operation_type.lower() in AUTONOMOUS_ALLOWED_TYPES


def requires_human_review(operation_type: str) -> bool:
    """Return True if this type always requires human review."""
    return operation_type.lower() in ALWAYS_HUMAN_REVIEW


# ---------------------------------------------------------------------------
# Hard limit validators
# ---------------------------------------------------------------------------

def enforce_max_per_cycle(requested: int, config_max: int) -> int:
    """Return the effective per-cycle limit (respects HARD_MAX_PER_CYCLE)."""
    return min(requested, config_max, HARD_MAX_PER_CYCLE)


def enforce_min_trust(trust_score: float, config_threshold: float) -> float:
    """Return the effective trust threshold (respects HARD_MIN_TRUST)."""
    return max(config_threshold, HARD_MIN_TRUST)


def enforce_max_rollback_rate(config_threshold: float) -> float:
    """Return the effective rollback threshold (respects HARD_MAX_ROLLBACK_RATE)."""
    return min(config_threshold, HARD_MAX_ROLLBACK_RATE)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def get_limits_summary() -> dict:
    """Return a human-readable summary of all hard limits."""
    return {
        "hard_max_per_cycle": HARD_MAX_PER_CYCLE,
        "hard_max_per_day": HARD_MAX_PER_DAY,
        "hard_min_trust": HARD_MIN_TRUST,
        "hard_max_rollback_rate": HARD_MAX_ROLLBACK_RATE,
        "autonomous_allowed_types": sorted(AUTONOMOUS_ALLOWED_TYPES),
        "always_human_review_types": sorted(ALWAYS_HUMAN_REVIEW),
        "today_count": get_today_count(),
    }
