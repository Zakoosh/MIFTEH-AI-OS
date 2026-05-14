"""
risk_controller.py — Risk gate for the Autonomous Operational Loops Layer.

Evaluates whether a proposal is cleared for autonomous execution.
Applies both hard limits (safety_limits.py) and soft trust-based gates.
"""

from __future__ import annotations

from .models import AutonomyConfig, RiskGateResult, TrustScore
from .safety_limits import (
    enforce_min_trust,
    enforce_max_rollback_rate,
    is_autonomous_allowed_type,
    requires_human_review,
    HARD_MIN_TRUST,
    HARD_MAX_ROLLBACK_RATE,
)
from .trust_scores import get_trust_manager


class RiskController:
    """
    Evaluates the risk gate for a given proposal before autonomous execution.

    Gate checks (in order):
    1. Operation type is in autonomous allowed list
    2. Operation type does not require human review
    3. Trust score >= effective threshold (max of config + hard limit)
    4. Rollback rate <= effective threshold (min of config + hard limit)
    5. Trust score is not suspended
    """

    def evaluate(
        self,
        proposal_id: str,
        proposal_type: str,
        project_id: str,
        config: AutonomyConfig,
    ) -> RiskGateResult:
        """Run all risk gate checks and return a RiskGateResult."""

        reasons_blocked: list[str] = []
        reasons_allowed: list[str] = []

        # Derive effective thresholds respecting hard limits
        eff_trust_threshold = enforce_min_trust(config.trust_threshold, HARD_MIN_TRUST)
        eff_rollback_threshold = enforce_max_rollback_rate(config.rollback_threshold)

        # Load trust score
        ts = get_trust_manager().get(
            project_id=project_id,
            proposal_type=proposal_type,
            initial_score=config.initial_trust_score,
            trust_threshold=eff_trust_threshold,
            rollback_threshold=eff_rollback_threshold,
        )

        # ── Check 1: Operation type allowed for autonomous runs ────────
        if not is_autonomous_allowed_type(proposal_type):
            reasons_blocked.append(
                f"Operation type '{proposal_type}' is not in the autonomous allowed list"
            )
        else:
            reasons_allowed.append(f"Operation type '{proposal_type}' is autonomy-eligible")

        # ── Check 2: Human review required ────────────────────────────
        if requires_human_review(proposal_type):
            reasons_blocked.append(
                f"Operation type '{proposal_type}' always requires human review"
            )

        # ── Check 3: Trust score gate ──────────────────────────────────
        if ts.score < eff_trust_threshold:
            reasons_blocked.append(
                f"Trust score {ts.score:.1f} is below threshold {eff_trust_threshold:.1f}"
            )
        else:
            reasons_allowed.append(
                f"Trust score {ts.score:.1f} meets threshold {eff_trust_threshold:.1f}"
            )

        # ── Check 4: Rollback rate gate ────────────────────────────────
        if ts.rollback_rate > eff_rollback_threshold:
            reasons_blocked.append(
                f"Rollback rate {ts.rollback_rate:.1f}% exceeds threshold {eff_rollback_threshold:.1f}%"
            )
        else:
            reasons_allowed.append(
                f"Rollback rate {ts.rollback_rate:.1f}% within threshold {eff_rollback_threshold:.1f}%"
            )

        # ── Check 5: Suspension status ─────────────────────────────────
        if ts.suspended:
            reasons_blocked.append(
                f"Type '{proposal_type}' for project '{project_id}' is suspended: {ts.suspension_reason}"
            )
        else:
            reasons_allowed.append("Not suspended")

        # ── Check 6: Autonomy master switch ────────────────────────────
        if not config.enabled:
            reasons_blocked.append("Autonomy engine is globally disabled")

        allowed = len(reasons_blocked) == 0

        return RiskGateResult(
            proposal_id=proposal_id,
            proposal_type=proposal_type,
            project_id=project_id,
            allowed=allowed,
            trust_score=ts.score,
            rollback_rate=ts.rollback_rate,
            reasons_blocked=reasons_blocked,
            reasons_allowed=reasons_allowed,
        )

    def quick_check(
        self,
        proposal_type: str,
        project_id: str,
        config: AutonomyConfig,
    ) -> bool:
        """Fast boolean check — True if proposal type is cleared for auto-apply."""
        eff_trust = enforce_min_trust(config.trust_threshold, HARD_MIN_TRUST)
        eff_rollback = enforce_max_rollback_rate(config.rollback_threshold)

        if not config.enabled:
            return False
        if not is_autonomous_allowed_type(proposal_type):
            return False
        if requires_human_review(proposal_type):
            return False

        ts = get_trust_manager().get(
            project_id=project_id,
            proposal_type=proposal_type,
            initial_score=config.initial_trust_score,
            trust_threshold=eff_trust,
            rollback_threshold=eff_rollback,
        )
        return (
            ts.score >= eff_trust
            and ts.rollback_rate <= eff_rollback
            and not ts.suspended
        )


# Module-level singleton
_controller = RiskController()


def get_risk_controller() -> RiskController:
    return _controller
