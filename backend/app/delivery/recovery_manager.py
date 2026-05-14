"""
recovery_manager.py — Handles recovery when a delivery phase fails validation.
"""

from __future__ import annotations

from . import delivery_memory as mem
from .models import RecoveryRecord, RECOVERY_RETRY, RECOVERY_ROLLBACK, RECOVERY_SKIP, _sim_success


# Recovery action selection: (trigger, phase) → action
_ACTION_MAP: dict[tuple[str, str], str] = {
    ("validation_failed", "preparation"):    RECOVERY_RETRY,
    ("validation_failed", "implementation"): RECOVERY_RETRY,
    ("validation_failed", "review"):         RECOVERY_ROLLBACK,
    ("validation_failed", "deployment"):     RECOVERY_ROLLBACK,
    ("validation_failed", "validation"):     RECOVERY_ROLLBACK,
    ("step_failed",       "preparation"):    RECOVERY_RETRY,
    ("step_failed",       "implementation"): RECOVERY_RETRY,
    ("step_failed",       "review"):         RECOVERY_SKIP,
    ("step_failed",       "deployment"):     RECOVERY_ROLLBACK,
}

_DETAILS: dict[str, str] = {
    RECOVERY_RETRY:    "Retrying phase with extended timeout and additional verification.",
    RECOVERY_ROLLBACK: "Rolling back to previous stable state; snapshot restored.",
    RECOVERY_SKIP:     "Skipping non-critical step; proceeding with reduced scope.",
    RECOVERY_SKIP:     "Skipping non-critical step; proceeding with reduced scope.",
}


def recover(
    plan_id: str,
    run_id: str,
    phase: str,
    trigger: str,
) -> RecoveryRecord:
    action  = _ACTION_MAP.get((trigger, phase), RECOVERY_RETRY)
    seed    = f"{plan_id}_{phase}_{trigger}_recovery"
    # Retry and skip succeed 90%; rollback succeeds 98%
    rate    = 0.98 if action == RECOVERY_ROLLBACK else 0.90
    success = _sim_success(seed, rate)

    rec = RecoveryRecord(
        recovery_id    = f"rec_{plan_id}_{phase}",
        plan_id        = plan_id,
        run_id         = run_id,
        phase          = phase,
        trigger        = trigger,
        action         = action,
        action_details = _DETAILS.get(action, "Recovery action taken."),
        success        = success,
    )
    mem.save_recovery(rec.to_dict())
    return rec


_instance = None


def get_recovery_manager():
    global _instance
    if _instance is None:
        _instance = type("RecoveryManager", (), {
            "recover": staticmethod(recover),
            "list_all": lambda self: mem.list_recovery(),
        })()
    return _instance
