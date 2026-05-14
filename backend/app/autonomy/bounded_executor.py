"""
bounded_executor.py — Enforces execution caps for the Autonomy Layer.

Ensures the engine never exceeds:
- max_per_cycle: proposals applied within a single cycle
- max_per_day: proposals applied across all cycles in a calendar day

Also tracks which proposals have already been autonomously applied to
prevent duplicate runs without human re-authorization.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import AutonomyConfig
from .safety_limits import (
    enforce_max_per_cycle,
    increment_today_count,
    is_daily_cap_reached,
    get_today_count,
    HARD_MAX_PER_CYCLE,
    HARD_MAX_PER_DAY,
)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

_APPLIED_PATH = Path("app/memory/autonomy/config/applied_proposals.json")


def _ensure_dirs() -> None:
    _APPLIED_PATH.parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Applied proposal registry
# ---------------------------------------------------------------------------

def _load_applied() -> dict:
    _ensure_dirs()
    if not _APPLIED_PATH.exists():
        return {}
    try:
        return json.loads(_APPLIED_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_applied(data: dict) -> None:
    _ensure_dirs()
    try:
        _APPLIED_PATH.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


def mark_proposal_applied(proposal_id: str, operation_id: str, cycle_id: str) -> None:
    """Record that a proposal has been autonomously applied."""
    from .models import now_iso
    data = _load_applied()
    data[proposal_id] = {
        "operation_id": operation_id,
        "cycle_id": cycle_id,
        "applied_at": now_iso(),
    }
    _save_applied(data)


def is_proposal_applied(proposal_id: str) -> bool:
    """Return True if this proposal has already been autonomously applied."""
    data = _load_applied()
    return proposal_id in data


def list_applied_proposals() -> dict:
    """Return all autonomously-applied proposal records."""
    return _load_applied()


def reset_applied_proposals() -> None:
    """Clear the applied proposals registry (use with care)."""
    _save_applied({})


# ---------------------------------------------------------------------------
# BoundedExecutor
# ---------------------------------------------------------------------------

class BoundedExecutor:
    """
    Enforces bounded execution during an autonomous cycle.

    Usage:
        executor = BoundedExecutor(config)
        while executor.can_apply():
            apply_one()
            executor.record_applied()
        executor.commit()   # persists daily count
    """

    def __init__(self, config: AutonomyConfig, override_max: int = 0) -> None:
        self.config = config
        self._cycle_limit = enforce_max_per_cycle(
            override_max if override_max > 0 else config.max_per_cycle,
            config.max_per_cycle,
        )
        self._cycle_count = 0
        self._daily_count_at_start = get_today_count()
        self._committed = False

    @property
    def cycle_limit(self) -> int:
        return self._cycle_limit

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    def can_apply(self) -> tuple[bool, str]:
        """
        Check whether another apply is permitted.
        Returns (allowed, reason_if_blocked).
        """
        # Cycle cap
        if self._cycle_count >= self._cycle_limit:
            return False, f"Cycle cap reached: {self._cycle_count}/{self._cycle_limit}"

        # Daily cap
        cap_reached, today_count, limit = is_daily_cap_reached(self.config.max_per_day)
        if cap_reached:
            return False, f"Daily cap reached: {today_count}/{limit}"

        return True, ""

    def record_applied(self) -> None:
        """Record that one apply was consumed from the cycle budget."""
        self._cycle_count += 1

    def remaining_in_cycle(self) -> int:
        return max(0, self._cycle_limit - self._cycle_count)

    def commit(self) -> int:
        """Persist the cycle count to the daily counter. Returns new daily total."""
        if not self._committed and self._cycle_count > 0:
            self._committed = True
            return increment_today_count(self._cycle_count)
        return get_today_count()

    def execution_summary(self) -> dict[str, Any]:
        return {
            "cycle_limit": self._cycle_limit,
            "cycle_applied": self._cycle_count,
            "cycle_remaining": self.remaining_in_cycle(),
            "daily_count": get_today_count(),
            "daily_limit": min(self.config.max_per_day, HARD_MAX_PER_DAY),
        }
