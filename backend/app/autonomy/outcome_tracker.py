"""
outcome_tracker.py — Records and aggregates operation outcomes.

Every autonomous apply operation produces an OperationOutcome that is
persisted here and used by the feedback loop and trust scoring.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    OperationOutcome,
    OUTCOME_SUCCESS,
    OUTCOME_FAILURE,
    OUTCOME_ROLLBACK,
    OUTCOME_SKIPPED,
    OUTCOME_DRY_RUN,
)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

OUTCOMES_DIR = Path("app/memory/autonomy/outcomes")


def _ensure_dirs() -> None:
    OUTCOMES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# OutcomeTracker
# ---------------------------------------------------------------------------

class OutcomeTracker:
    """
    Records operation outcomes and exposes aggregated analytics.

    Aggregations available:
    - Per proposal_type: success_rate, rollback_rate, failure_rate
    - Per project: total counts
    - Overall cycle summaries
    """

    def record(
        self,
        operation_id: str,
        proposal_id: str,
        project_id: str,
        proposal_type: str,
        outcome: str,
        simulated: bool = False,
        dry_run: bool = False,
        details: dict[str, Any] | None = None,
    ) -> OperationOutcome:
        """Persist an outcome record and return the OperationOutcome."""
        _ensure_dirs()
        entry = OperationOutcome(
            operation_id=operation_id,
            proposal_id=proposal_id,
            project_id=project_id,
            proposal_type=proposal_type,
            outcome=outcome,
            simulated=simulated,
            dry_run=dry_run,
            details=details or {},
        )
        path = OUTCOMES_DIR / f"{entry.outcome_id}.json"
        try:
            path.write_text(
                json.dumps(entry.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass
        return entry

    def list_all(self) -> list[OperationOutcome]:
        """Return all outcomes, newest first."""
        _ensure_dirs()
        results = []
        for file in OUTCOMES_DIR.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                results.append(OperationOutcome.from_dict(data))
            except Exception:
                pass
        results.sort(key=lambda x: x.timestamp, reverse=True)
        return results

    def list_for_type(self, project_id: str, proposal_type: str) -> list[OperationOutcome]:
        """Return outcomes filtered by project+type."""
        return [
            o for o in self.list_all()
            if o.project_id == project_id and o.proposal_type == proposal_type
        ]

    def aggregate_by_type(self) -> dict[str, dict]:
        """
        Aggregate outcomes per (project_id, proposal_type) key.

        Returns dict keyed by "{project_id}:{proposal_type}":
          {
            "total": int,
            "success": int, "failure": int, "rollback": int,
            "skipped": int, "dry_run": int,
            "success_rate": float, "rollback_rate": float, "failure_rate": float
          }
        """
        aggregates: dict[str, dict] = {}
        for outcome in self.list_all():
            key = f"{outcome.project_id}:{outcome.proposal_type}"
            if key not in aggregates:
                aggregates[key] = {
                    "project_id": outcome.project_id,
                    "proposal_type": outcome.proposal_type,
                    "total": 0,
                    OUTCOME_SUCCESS: 0,
                    OUTCOME_FAILURE: 0,
                    OUTCOME_ROLLBACK: 0,
                    OUTCOME_SKIPPED: 0,
                    OUTCOME_DRY_RUN: 0,
                }
            agg = aggregates[key]
            agg["total"] += 1
            agg[outcome.outcome] = agg.get(outcome.outcome, 0) + 1

        # Compute rates
        for agg in aggregates.values():
            t = agg["total"]
            agg["success_rate"] = round((agg.get(OUTCOME_SUCCESS, 0) / t) * 100, 1) if t else 0.0
            agg["rollback_rate"] = round((agg.get(OUTCOME_ROLLBACK, 0) / t) * 100, 1) if t else 0.0
            agg["failure_rate"] = round((agg.get(OUTCOME_FAILURE, 0) / t) * 100, 1) if t else 0.0

        return aggregates

    def aggregate_by_project(self) -> dict[str, dict]:
        """Aggregate outcomes per project_id."""
        agg: dict[str, dict] = {}
        for outcome in self.list_all():
            pid = outcome.project_id
            if pid not in agg:
                agg[pid] = {
                    "project_id": pid,
                    "total": 0,
                    OUTCOME_SUCCESS: 0,
                    OUTCOME_FAILURE: 0,
                    OUTCOME_ROLLBACK: 0,
                }
            agg[pid]["total"] += 1
            agg[pid][outcome.outcome] = agg[pid].get(outcome.outcome, 0) + 1
        return agg

    def get_rollback_rate(self, project_id: str, proposal_type: str) -> float:
        """Compute rollback rate for a specific (project, type)."""
        outcomes = self.list_for_type(project_id, proposal_type)
        if not outcomes:
            return 0.0
        real = [o for o in outcomes if o.outcome in (OUTCOME_SUCCESS, OUTCOME_FAILURE, OUTCOME_ROLLBACK)]
        if not real:
            return 0.0
        rollbacks = sum(1 for o in real if o.outcome == OUTCOME_ROLLBACK)
        return round((rollbacks / len(real)) * 100, 2)

    def overall_metrics(self) -> dict[str, Any]:
        """Return top-level metrics for the status endpoint."""
        all_outcomes = self.list_all()
        total = len(all_outcomes)
        if total == 0:
            return {
                "total_operations": 0,
                "success_count": 0, "failure_count": 0,
                "rollback_count": 0, "skipped_count": 0,
                "dry_run_count": 0,
                "overall_success_rate": 0.0,
                "overall_rollback_rate": 0.0,
            }

        counts = {OUTCOME_SUCCESS: 0, OUTCOME_FAILURE: 0, OUTCOME_ROLLBACK: 0,
                  OUTCOME_SKIPPED: 0, OUTCOME_DRY_RUN: 0}
        for o in all_outcomes:
            counts[o.outcome] = counts.get(o.outcome, 0) + 1

        applied = counts[OUTCOME_SUCCESS] + counts[OUTCOME_FAILURE] + counts[OUTCOME_ROLLBACK]
        return {
            "total_operations": total,
            "success_count": counts[OUTCOME_SUCCESS],
            "failure_count": counts[OUTCOME_FAILURE],
            "rollback_count": counts[OUTCOME_ROLLBACK],
            "skipped_count": counts[OUTCOME_SKIPPED],
            "dry_run_count": counts[OUTCOME_DRY_RUN],
            "overall_success_rate": round(
                (counts[OUTCOME_SUCCESS] / applied * 100) if applied else 0, 1
            ),
            "overall_rollback_rate": round(
                (counts[OUTCOME_ROLLBACK] / applied * 100) if applied else 0, 1
            ),
        }


# Module-level singleton
_tracker = OutcomeTracker()


def get_tracker() -> OutcomeTracker:
    return _tracker
