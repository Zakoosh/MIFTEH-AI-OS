"""
feedback_loop.py — Adaptive feedback and learning for the Autonomy Layer.

After each apply outcome, the feedback loop:
1. Updates the trust score (gain on success, loss on failure/rollback)
2. Records a FeedbackEntry explaining what changed and why
3. Flags suspended types for operational awareness
4. Produces adaptive insights from outcome patterns
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    AutonomyConfig,
    FeedbackEntry,
    OperationOutcome,
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_ROLLBACK,
    OUTCOME_DRY_RUN,
    OUTCOME_SKIPPED,
)
from .trust_scores import get_trust_manager


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

FEEDBACK_DIR = Path("app/memory/autonomy/feedback")


def _ensure_dirs() -> None:
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# FeedbackLoop
# ---------------------------------------------------------------------------

class FeedbackLoop:
    """
    Processes an OperationOutcome and updates trust scores + records insights.

    Learning rules:
    - SUCCESS  → trust += gain (capped at 100)
    - FAILURE  → trust -= loss (floored at 0); check suspension
    - ROLLBACK → trust -= loss; increment rollback counter; check suspension
    - SKIPPED / DRY_RUN → no trust change
    """

    def process(
        self,
        outcome: OperationOutcome,
        cycle_id: str,
        config: AutonomyConfig,
    ) -> FeedbackEntry:
        """
        Process a single outcome and return the resulting FeedbackEntry.
        Also updates the trust score in the trust store.
        """
        _ensure_dirs()
        tm = get_trust_manager()

        if outcome.outcome == OUTCOME_SUCCESS:
            ts, old_score, new_score = tm.apply_success(
                project_id=outcome.project_id,
                proposal_type=outcome.proposal_type,
                gain=config.trust_gain_on_success,
                trust_threshold=config.trust_threshold,
                rollback_threshold=config.rollback_threshold,
                initial_score=config.initial_trust_score,
            )
            action = "trust_increased"
            insight = (
                f"Successful apply of '{outcome.proposal_type}' for '{outcome.project_id}'. "
                f"Trust increased {old_score:.1f} → {new_score:.1f}."
            )

        elif outcome.outcome in (OUTCOME_FAILURE, OUTCOME_ROLLBACK):
            is_rollback = outcome.outcome == OUTCOME_ROLLBACK
            ts, old_score, new_score = tm.apply_failure(
                project_id=outcome.project_id,
                proposal_type=outcome.proposal_type,
                loss=config.trust_loss_on_failure,
                rollback=is_rollback,
                trust_threshold=config.trust_threshold,
                rollback_threshold=config.rollback_threshold,
                suspension_threshold=config.suspension_threshold,
                initial_score=config.initial_trust_score,
            )
            if ts.suspended:
                action = "suspended"
                insight = (
                    f"'{outcome.proposal_type}' for '{outcome.project_id}' suspended. "
                    f"Rollback rate {ts.rollback_rate:.1f}% exceeds threshold "
                    f"{config.rollback_threshold:.1f}%. "
                    f"Trust: {old_score:.1f} → {new_score:.1f}."
                )
            else:
                action = "trust_decreased"
                verb = "Rollback" if is_rollback else "Failure"
                insight = (
                    f"{verb} on '{outcome.proposal_type}' for '{outcome.project_id}'. "
                    f"Trust decreased {old_score:.1f} → {new_score:.1f}. "
                    f"Rollback rate: {ts.rollback_rate:.1f}%."
                )

        else:
            # SKIPPED or DRY_RUN — no trust change
            ts = tm.get(
                outcome.project_id,
                outcome.proposal_type,
                config.initial_trust_score,
                config.trust_threshold,
                config.rollback_threshold,
            )
            old_score = ts.score
            new_score = ts.score
            action = "no_change"
            insight = f"Outcome '{outcome.outcome}' — no trust adjustment."

        entry = FeedbackEntry(
            cycle_id=cycle_id,
            proposal_id=outcome.proposal_id,
            proposal_type=outcome.proposal_type,
            project_id=outcome.project_id,
            insight=insight,
            action_taken=action,
            old_score=old_score,
            new_score=new_score,
        )

        self._save(entry)
        return entry

    def generate_insights(self, outcomes: list[OperationOutcome]) -> list[str]:
        """Generate human-readable operational insights from a set of outcomes."""
        insights = []

        if not outcomes:
            return ["No outcomes to analyze."]

        successes = [o for o in outcomes if o.outcome == OUTCOME_SUCCESS]
        failures = [o for o in outcomes if o.outcome == OUTCOME_FAILURE]
        rollbacks = [o for o in outcomes if o.outcome == OUTCOME_ROLLBACK]

        if successes:
            types = list({o.proposal_type for o in successes})
            insights.append(f"{len(successes)} successful applies across types: {', '.join(types)}.")

        if rollbacks:
            types = list({o.proposal_type for o in rollbacks})
            insights.append(
                f"ALERT: {len(rollbacks)} rollback(s) detected for types: {', '.join(types)}. "
                "Trust scores have been reduced."
            )

        if failures:
            types = list({o.proposal_type for o in failures})
            insights.append(
                f"{len(failures)} failure(s) on types: {', '.join(types)}. "
                "Investigate apply logs."
            )

        total = len(outcomes)
        success_rate = round(len(successes) / total * 100, 1) if total else 0
        insights.append(f"Cycle success rate: {success_rate}% ({len(successes)}/{total} applied).")

        return insights

    def list_all(self) -> list[FeedbackEntry]:
        """Return all feedback entries, newest first."""
        _ensure_dirs()
        results = []
        for file in FEEDBACK_DIR.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                results.append(FeedbackEntry.from_dict(data))
            except Exception:
                pass
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results

    def list_for_cycle(self, cycle_id: str) -> list[FeedbackEntry]:
        """Return all feedback entries for a specific cycle."""
        return [e for e in self.list_all() if e.cycle_id == cycle_id]

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save(self, entry: FeedbackEntry) -> None:
        path = FEEDBACK_DIR / f"{entry.feedback_id}.json"
        try:
            path.write_text(
                json.dumps(entry.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass


# Module-level singleton
_feedback_loop = FeedbackLoop()


def get_feedback_loop() -> FeedbackLoop:
    return _feedback_loop
