"""
checkpoint_manager.py — Manages validation checkpoints across delivery phases.
"""

from __future__ import annotations

from typing import Any

from . import delivery_memory as mem
from .models import ValidationCheckpoint, VALIDATION_PASSED
from .validation_runner import run_validation


class CheckpointManager:

    def run_and_save(
        self,
        plan_id: str,
        run_id: str,
        phase: str,
        phase_number: int,
        task_type: str,
        work_item_id: str,
    ) -> ValidationCheckpoint:
        cp = run_validation(plan_id, run_id, phase, phase_number, task_type, work_item_id)
        mem.save_checkpoint(cp.to_dict())
        return cp

    def passed(self, checkpoint: ValidationCheckpoint) -> bool:
        return checkpoint.result == VALIDATION_PASSED

    def list_for_plan(self, plan_id: str) -> list[dict[str, Any]]:
        return mem.list_checkpoints(plan_id)

    def list_all(self) -> list[dict[str, Any]]:
        return mem.list_checkpoints()

    def pass_rate(self) -> float:
        all_cp = self.list_all()
        if not all_cp:
            return 100.0
        passed = sum(1 for c in all_cp if c.get("result") == VALIDATION_PASSED)
        return round(passed / len(all_cp) * 100, 1)


_instance: CheckpointManager | None = None


def get_checkpoint_manager() -> CheckpointManager:
    global _instance
    if _instance is None:
        _instance = CheckpointManager()
    return _instance
