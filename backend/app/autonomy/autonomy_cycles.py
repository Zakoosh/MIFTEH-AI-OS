"""
autonomy_cycles.py — Cycle management for the Autonomous Operational Loops Layer.

Manages the lifecycle of autonomy cycles: creation, persistence, and history.
A cycle represents one bounded autonomous execution run.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import AutonomyCycle, CYCLE_COMPLETED, CYCLE_FAILED, CYCLE_ABORTED


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

CYCLES_DIR = Path("app/memory/autonomy/cycles")


def _ensure_dirs() -> None:
    CYCLES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# CycleManager
# ---------------------------------------------------------------------------

class CycleManager:
    """Manages creation, persistence, and retrieval of AutonomyCycles."""

    def create(
        self,
        triggered_by: str = "manual",
        dry_run: bool = False,
    ) -> AutonomyCycle:
        """Create and persist a new cycle in RUNNING state."""
        _ensure_dirs()
        cycle = AutonomyCycle(triggered_by=triggered_by, dry_run=dry_run)
        self._save(cycle)
        return cycle

    def update(self, cycle: AutonomyCycle) -> None:
        """Persist current cycle state."""
        self._save(cycle)

    def complete(
        self,
        cycle: AutonomyCycle,
        error: str = "",
    ) -> AutonomyCycle:
        """Mark a cycle as completed (or failed if error is set)."""
        status = CYCLE_FAILED if error else CYCLE_COMPLETED
        cycle.complete(status=status, error=error)
        self._save(cycle)
        return cycle

    def abort(self, cycle: AutonomyCycle, reason: str = "") -> AutonomyCycle:
        """Mark a cycle as aborted."""
        cycle.complete(status=CYCLE_ABORTED, error=reason)
        self._save(cycle)
        return cycle

    def get(self, cycle_id: str) -> AutonomyCycle | None:
        """Load a specific cycle by ID."""
        _ensure_dirs()
        path = CYCLES_DIR / f"{cycle_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return AutonomyCycle.from_dict(data)
        except Exception:
            return None

    def list_all(self) -> list[AutonomyCycle]:
        """Return all cycles, newest first."""
        _ensure_dirs()
        cycles = []
        for file in CYCLES_DIR.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                cycles.append(AutonomyCycle.from_dict(data))
            except Exception:
                pass
        cycles.sort(key=lambda c: c.started_at, reverse=True)
        return cycles

    def list_as_dicts(self) -> list[dict]:
        return [c.to_dict() for c in self.list_all()]

    def cycle_metrics(self) -> dict:
        """Aggregate metrics across all cycles."""
        cycles = self.list_all()
        total = len(cycles)
        if total == 0:
            return {
                "total_cycles": 0,
                "completed": 0, "failed": 0, "aborted": 0,
                "total_applied": 0, "total_evaluated": 0,
                "avg_applied_per_cycle": 0.0,
            }

        completed = sum(1 for c in cycles if c.status == CYCLE_COMPLETED)
        failed = sum(1 for c in cycles if c.status == CYCLE_FAILED)
        aborted = sum(1 for c in cycles if c.status == CYCLE_ABORTED)
        total_applied = sum(c.proposals_applied for c in cycles)
        total_evaluated = sum(c.proposals_evaluated for c in cycles)

        return {
            "total_cycles": total,
            "completed": completed,
            "failed": failed,
            "aborted": aborted,
            "total_applied": total_applied,
            "total_evaluated": total_evaluated,
            "avg_applied_per_cycle": round(total_applied / total, 2) if total else 0.0,
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save(self, cycle: AutonomyCycle) -> None:
        _ensure_dirs()
        path = CYCLES_DIR / f"{cycle.cycle_id}.json"
        try:
            path.write_text(
                json.dumps(cycle.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass


# Module-level singleton
_manager = CycleManager()


def get_cycle_manager() -> CycleManager:
    return _manager
