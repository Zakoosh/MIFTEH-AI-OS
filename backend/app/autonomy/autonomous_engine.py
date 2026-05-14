"""
autonomous_engine.py — Core orchestrator for the Autonomous Operational Loops Layer.

Execution flow per cycle:
  Proposal Selection
  → Risk Validation
  → Preview (via apply layer)
  → Apply (via apply layer)
  → Outcome Tracking
  → Trust Score Update
  → Feedback Loop
  → Cycle Record Saved

Safety guarantees:
- Master kill switch (config.enabled)
- Bounded by max_per_cycle and max_per_day (with hard limits)
- Only low-risk proposals via trust gate
- All applies are backed by rollback support (from apply layer)
- Full audit trail maintained
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    AutonomyCycle,
    AutonomyConfig,
    CYCLE_ABORTED,
    CYCLE_COMPLETED,
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_ROLLBACK,
    OUTCOME_SKIPPED,
    OUTCOME_DRY_RUN,
)
from .proposal_selector import get_selector
from .risk_controller import get_risk_controller
from .bounded_executor import BoundedExecutor, mark_proposal_applied
from .outcome_tracker import get_tracker
from .feedback_loop import get_feedback_loop
from .trust_scores import get_trust_manager
from .autonomy_cycles import get_cycle_manager
from .safety_limits import get_limits_summary


# ---------------------------------------------------------------------------
# Config storage
# ---------------------------------------------------------------------------

CONFIG_PATH = Path("app/memory/autonomy/config/config.json")


def _ensure_dirs() -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> AutonomyConfig:
    """Load autonomy config from disk, or return defaults."""
    _ensure_dirs()
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return AutonomyConfig.from_dict(data)
        except Exception:
            pass
    return AutonomyConfig()


def save_config(config: AutonomyConfig) -> None:
    """Persist autonomy config to disk."""
    _ensure_dirs()
    try:
        CONFIG_PATH.write_text(
            json.dumps(config.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    except OSError:
        pass


# ---------------------------------------------------------------------------
# AutonomousEngine
# ---------------------------------------------------------------------------

class AutonomousEngine:
    """
    Runs bounded autonomous operational cycles.

    Each call to run_cycle():
    1. Loads and validates the config
    2. Checks daily cap
    3. Selects eligible proposals (trust-gated, low-risk)
    4. For each selected proposal (up to cycle limit):
       a. Re-checks the risk gate
       b. Calls the apply layer (dry_run or real)
       c. Records outcome
       d. Updates trust score via feedback loop
    5. Saves cycle record
    6. Returns cycle summary
    """

    def __init__(self) -> None:
        self._selector = get_selector()
        self._risk = get_risk_controller()
        self._tracker = get_tracker()
        self._feedback = get_feedback_loop()
        self._trust = get_trust_manager()
        self._cycles = get_cycle_manager()

    # ------------------------------------------------------------------
    # Main cycle runner
    # ------------------------------------------------------------------

    def run_cycle(
        self,
        triggered_by: str = "manual",
        dry_run: bool = False,
        max_proposals: int = 0,
        project_filter: str = "",
    ) -> AutonomyCycle:
        """Execute one autonomous operational cycle."""

        config = load_config()

        # Create cycle record
        cycle = self._cycles.create(triggered_by=triggered_by, dry_run=dry_run)

        # ── Master kill switch ──────────────────────────────────────────
        if not config.enabled:
            cycle.summary = "Autonomy engine is disabled."
            return self._cycles.abort(cycle, reason="Engine disabled by config")

        # ── Bounded executor ────────────────────────────────────────────
        executor = BoundedExecutor(config, override_max=max_proposals)
        cap_ok, cap_msg = executor.can_apply()
        if not cap_ok:
            cycle.summary = f"Execution cap reached before cycle start: {cap_msg}"
            return self._cycles.abort(cycle, reason=cap_msg)

        # ── Select proposals ────────────────────────────────────────────
        try:
            selected = self._selector.select(
                config=config,
                max_count=executor.cycle_limit,
                project_filter=project_filter,
            )
        except Exception as exc:
            return self._cycles.abort(cycle, reason=f"Proposal selection error: {exc}")

        cycle.proposals_evaluated = self._count_total_proposals(project_filter)
        cycle.proposals_selected = len(selected)
        self._cycles.update(cycle)

        if not selected:
            cycle.summary = "No eligible proposals found for this cycle."
            return self._cycles.complete(cycle)

        # ── Apply loop ──────────────────────────────────────────────────
        for proposal_raw in selected:
            can_apply, block_reason = executor.can_apply()
            if not can_apply:
                cycle.proposals_skipped += 1
                continue

            proposal_id = proposal_raw.get("id", "")
            project_id = proposal_raw.get("project_id", "")
            proposal_type = proposal_raw.get("proposal_type", "")

            # Final risk gate before apply
            gate = self._risk.evaluate(proposal_id, proposal_type, project_id, config)
            if not gate.allowed:
                cycle.proposals_skipped += 1
                self._record_skipped(cycle, proposal_id, project_id, proposal_type, gate.reasons_blocked)
                continue

            # Apply via apply layer
            outcome_type, operation_id, result_details, simulated = self._execute_apply(
                proposal_id=proposal_id,
                project_id=project_id,
                proposal_type=proposal_type,
                dry_run=dry_run or config.dry_run_mode,
                config=config,
            )

            # Record outcome
            outcome = self._tracker.record(
                operation_id=operation_id,
                proposal_id=proposal_id,
                project_id=project_id,
                proposal_type=proposal_type,
                outcome=outcome_type,
                simulated=simulated,
                dry_run=dry_run or config.dry_run_mode,
                details=result_details,
            )

            # Feedback loop → trust update
            feedback = self._feedback.process(outcome, cycle.cycle_id, config)

            # Record in cycle
            cycle.outcome_ids.append(outcome.outcome_id)
            cycle.trust_updates[f"{project_id}:{proposal_type}"] = {
                "old_score": feedback.old_score,
                "new_score": feedback.new_score,
                "action": feedback.action_taken,
            }

            if outcome_type not in (OUTCOME_SKIPPED, OUTCOME_DRY_RUN):
                executor.record_applied()
                cycle.proposals_applied += 1
                mark_proposal_applied(proposal_id, operation_id, cycle.cycle_id)
            else:
                cycle.proposals_skipped += 1

        # ── Commit daily count ──────────────────────────────────────────
        if not (dry_run or config.dry_run_mode):
            executor.commit()

        # ── Generate insights ───────────────────────────────────────────
        all_outcomes = [
            self._tracker.record.__self__  # just to get the type
        ] if False else []

        feedback_entries = self._feedback.list_for_cycle(cycle.cycle_id)
        insights = self._feedback.generate_insights(
            [self._tracker.list_all()[0]] if self._tracker.list_all() else []
        )

        self._cycles.complete(cycle)
        return cycle

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _execute_apply(
        self,
        proposal_id: str,
        project_id: str,
        proposal_type: str,
        dry_run: bool,
        config: AutonomyConfig,
    ) -> tuple[str, str, dict[str, Any], bool]:
        """
        Call the apply layer for a single proposal.

        Returns (outcome_type, operation_id, result_details, simulated).
        """
        from app.apply.proposal_applier import get_applier

        try:
            result = get_applier().apply(proposal_id, dry_run=dry_run)

            if dry_run:
                outcome_type = OUTCOME_DRY_RUN
            elif result.applied:
                outcome_type = OUTCOME_SUCCESS
            else:
                outcome_type = OUTCOME_FAILURE

            return (
                outcome_type,
                result.operation_id,
                result.to_dict(),
                result.simulated,
            )

        except Exception as exc:
            return (
                OUTCOME_FAILURE,
                f"err_{proposal_id}",
                {"error": str(exc)},
                False,
            )

    def _record_skipped(
        self,
        cycle: AutonomyCycle,
        proposal_id: str,
        project_id: str,
        proposal_type: str,
        reasons: list[str],
    ) -> None:
        self._tracker.record(
            operation_id=f"skip_{proposal_id}",
            proposal_id=proposal_id,
            project_id=project_id,
            proposal_type=proposal_type,
            outcome=OUTCOME_SKIPPED,
            details={"reasons": reasons},
        )

    def _count_total_proposals(self, project_filter: str) -> int:
        try:
            from app.apply.proposal_applier import list_proposals
            all_p = list_proposals()
            if project_filter:
                return sum(1 for p in all_p if p.get("project_id") == project_filter)
            return len(all_p)
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # Read-only helpers
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Build the status payload for the /autonomy/status endpoint."""
        config = load_config()
        cycle_metrics = self._cycles.cycle_metrics()
        outcome_metrics = self._tracker.overall_metrics()
        trust_scores = self._trust.list_all(config.trust_threshold, config.rollback_threshold)
        limits = get_limits_summary()

        suspended = [ts for ts in trust_scores if ts.suspended]
        allowed = [ts for ts in trust_scores if ts.autonomous_apply_allowed]

        return {
            "status": "operational",
            "layer": "Autonomous Operational Loops Layer",
            "version": "1.0.0",
            "protected_dashboard": "yallaplays.com/admin/os",
            "enabled": config.enabled,
            "dry_run_mode": config.dry_run_mode,
            "config": config.to_dict(),
            "metrics": {
                **cycle_metrics,
                **outcome_metrics,
            },
            "trust_summary": {
                "total_tracked": len(trust_scores),
                "autonomous_allowed": len(allowed),
                "suspended": len(suspended),
                "suspended_types": [
                    f"{ts.project_id}:{ts.proposal_type}" for ts in suspended
                ],
            },
            "projects": ["yallaplays", "fionera"],
            "policy": {
                "max_risk_level": "low",
                "trust_threshold": config.trust_threshold,
                "rollback_threshold": config.rollback_threshold,
                "max_per_cycle": config.max_per_cycle,
                "max_per_day": config.max_per_day,
                **limits,
            },
        }

    def update_config(self, **kwargs: Any) -> AutonomyConfig:
        """Partially update the persisted config."""
        config = load_config()
        for key, val in kwargs.items():
            if val is not None and hasattr(config, key):
                setattr(config, key, val)
        save_config(config)
        return config


# Module-level singleton
_engine = AutonomousEngine()


def get_engine() -> AutonomousEngine:
    return _engine
