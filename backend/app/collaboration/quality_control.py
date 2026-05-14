"""
quality_control.py — Quality control workflows for collaborative sessions.

Runs structured QC checks after the review chain and consensus computation.
Produces a QualityReport that gates final session approval.

QC checks (all must pass for full approval):
  1. Role separation enforced
  2. All implementers reviewed
  3. Validator independence confirmed
  4. Consensus score above threshold
  5. No unresolved critical conflicts
  6. Review chain complete
  7. Minimum reviewer count satisfied
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import (
    ConsensusScore,
    ExecutionThread,
    QualityReport,
    ReviewRecord,
    now_iso,
)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

QUALITY_DIR = Path("app/memory/collaboration/quality")


def _ensure_dirs() -> None:
    QUALITY_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

MIN_REVIEWERS             = 1
MIN_VALIDATORS            = 1
CONSENSUS_PASS_THRESHOLD  = 75.0
QUALITY_SCORE_THRESHOLD   = 70.0


# ---------------------------------------------------------------------------
# QualityController
# ---------------------------------------------------------------------------

class QualityController:
    """
    Executes QC checks on a completed collaboration thread and emits a QualityReport.
    """

    def run(
        self,
        thread: ExecutionThread,
        reviews: list[ReviewRecord],
        consensus: ConsensusScore,
        unresolved_conflicts: int = 0,
    ) -> QualityReport:
        """Execute all QC checks and return a QualityReport."""
        _ensure_dirs()

        checks_passed: list[str] = []
        checks_failed: list[str] = []
        recommendations: list[str] = []

        implementers = set(thread.implementers)
        reviewers    = set(thread.reviewers)
        validators   = set(thread.validators)
        reviewer_agents = {r.reviewer_agent for r in reviews if r.role == "reviewer"}
        validator_agents = {r.reviewer_agent for r in reviews if r.role == "validator"}

        # ── Check 1: Role separation ────────────────────────────────────
        impl_rev_overlap = implementers & reviewers
        impl_val_overlap = implementers & validators
        rev_val_overlap  = reviewers & validators

        if not impl_rev_overlap and not impl_val_overlap and not rev_val_overlap:
            checks_passed.append("Role separation enforced: implementers ≠ reviewers ≠ validators")
        else:
            msg = "Role separation violated"
            if impl_rev_overlap:
                msg += f": implementer-reviewer overlap {impl_rev_overlap}"
            checks_failed.append(msg)
            recommendations.append("Reassign agents to enforce strict role separation")

        # ── Check 2: Review coverage ────────────────────────────────────
        reviewed_implementers = {r.reviewed_agent for r in reviews if r.role == "reviewer"}
        unreviewed = implementers - reviewed_implementers
        coverage = (len(reviewed_implementers) / len(implementers) * 100) if implementers else 100.0

        if not unreviewed:
            checks_passed.append(f"All implementers reviewed ({len(implementers)}/{len(implementers)})")
        else:
            checks_failed.append(f"Unreviewed implementers: {sorted(unreviewed)}")
            recommendations.append("Ensure all implementer contributions are reviewed")

        # ── Check 3: Validator independence ─────────────────────────────
        validator_independence = len(validator_agents & reviewers) == 0 and len(validator_agents & implementers) == 0
        if validator_independence:
            checks_passed.append("Validators are fully independent from implementers and reviewers")
        else:
            checks_failed.append("Validator independence compromised: overlap with implementers or reviewers")
            recommendations.append("Use dedicated validators not involved in implementation or review")

        # ── Check 4: Minimum reviewer count ─────────────────────────────
        unique_reviewers = len({r.reviewer_agent for r in reviews if r.role == "reviewer"})
        if unique_reviewers >= MIN_REVIEWERS:
            checks_passed.append(f"Minimum reviewer count met ({unique_reviewers} ≥ {MIN_REVIEWERS})")
        else:
            checks_failed.append(f"Insufficient reviewers: {unique_reviewers} < {MIN_REVIEWERS}")
            recommendations.append(f"Assign at least {MIN_REVIEWERS} reviewer agent(s)")

        # ── Check 5: Minimum validator count ────────────────────────────
        unique_validators = len({r.reviewer_agent for r in reviews if r.role == "validator"})
        if unique_validators >= MIN_VALIDATORS:
            checks_passed.append(f"Minimum validator count met ({unique_validators} ≥ {MIN_VALIDATORS})")
        else:
            checks_failed.append(f"Insufficient validators: {unique_validators} < {MIN_VALIDATORS}")
            recommendations.append(f"Assign at least {MIN_VALIDATORS} independent validator agent(s)")

        # ── Check 6: Consensus score ─────────────────────────────────────
        if consensus.consensus_score >= CONSENSUS_PASS_THRESHOLD:
            checks_passed.append(
                f"Consensus score {consensus.consensus_score} ≥ threshold {CONSENSUS_PASS_THRESHOLD}"
            )
        else:
            checks_failed.append(
                f"Consensus score {consensus.consensus_score} < threshold {CONSENSUS_PASS_THRESHOLD}"
            )
            recommendations.append("Improve implementation quality to raise consensus score")

        # ── Check 7: No unresolved conflicts ─────────────────────────────
        if unresolved_conflicts == 0:
            checks_passed.append("No unresolved conflicts")
        else:
            checks_failed.append(f"{unresolved_conflicts} unresolved conflict(s) remain")
            recommendations.append("Resolve all conflicts before final approval")

        # ── Check 8: Review chain completeness ───────────────────────────
        if thread.chain_id:
            checks_passed.append("Review chain completed and chained")
        else:
            checks_failed.append("Review chain not completed")
            recommendations.append("Complete the review chain before quality approval")

        # Compute quality score (% of checks passed, weighted)
        total_checks = len(checks_passed) + len(checks_failed)
        quality_score = round((len(checks_passed) / total_checks * 100), 1) if total_checks else 0.0

        # Blend with consensus score (50/50 weight)
        blended_quality = round((quality_score + consensus.consensus_score) / 2, 1)
        approved = (
            len(checks_failed) == 0
            and consensus.approved
            and blended_quality >= QUALITY_SCORE_THRESHOLD
        )

        report = QualityReport(
            thread_id=thread.thread_id,
            session_id=thread.session_id,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            quality_score=blended_quality,
            approved=approved,
            recommendations=recommendations,
            reviewer_coverage=round(coverage, 1),
            validator_independence=validator_independence,
        )

        self._save(report)
        return report

    def list_all(self) -> list[QualityReport]:
        _ensure_dirs()
        reports = []
        for f in QUALITY_DIR.glob("*.json"):
            try:
                reports.append(QualityReport.from_dict(json.loads(f.read_text(encoding="utf-8"))))
            except Exception:
                pass
        reports.sort(key=lambda r: r.timestamp, reverse=True)
        return reports

    def analytics(self) -> dict:
        all_r = self.list_all()
        if not all_r:
            return {"total": 0, "approved": 0, "rejected": 0, "avg_quality_score": 0.0}
        approved = sum(1 for r in all_r if r.approved)
        avg_qs   = round(sum(r.quality_score for r in all_r) / len(all_r), 1)
        return {
            "total": len(all_r),
            "approved": approved,
            "rejected": len(all_r) - approved,
            "avg_quality_score": avg_qs,
            "approval_rate": round(approved / len(all_r) * 100, 1),
        }

    def _save(self, r: QualityReport) -> None:
        _ensure_dirs()
        path = QUALITY_DIR / f"{r.report_id}.json"
        try:
            path.write_text(json.dumps(r.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


# Module-level singleton
_controller = QualityController()


def get_quality_controller() -> QualityController:
    return _controller
