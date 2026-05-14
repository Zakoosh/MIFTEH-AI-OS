"""
proposal_selector.py — Selects and ranks proposals for autonomous execution.

Selection criteria (all must pass):
1. risk_level == "low"
2. proposal_type in AUTONOMOUS_ALLOWED_TYPES
3. Not already autonomously applied
4. Risk gate: trust_score >= threshold AND rollback_rate <= threshold
5. Not suspended

Ranking: highest trust score first.
"""

from __future__ import annotations

from typing import Any

from .models import AutonomyConfig, TrustScore
from .safety_limits import is_autonomous_allowed_type
from .trust_scores import get_trust_manager
from .bounded_executor import is_proposal_applied
from .risk_controller import get_risk_controller


class ProposalSelector:
    """
    Selects eligible proposals from the apply layer registry
    and ranks them by trust score for autonomous execution.
    """

    def select(
        self,
        config: AutonomyConfig,
        max_count: int = 0,
        project_filter: str = "",
    ) -> list[dict[str, Any]]:
        """
        Return a ranked list of proposals eligible for autonomous apply.

        Args:
            config: Current autonomy configuration.
            max_count: Override per-cycle limit (0 = use config default).
            project_filter: Restrict to a specific project_id ("" = all projects).

        Returns:
            List of proposal dicts, ranked by trust score descending.
        """
        from app.apply.proposal_applier import list_proposals

        all_proposals = list_proposals()
        limit = max_count if max_count > 0 else config.max_per_cycle
        tm = get_trust_manager()
        rc = get_risk_controller()

        candidates: list[tuple[float, dict]] = []

        for proposal in all_proposals:
            pid = proposal.get("project_id", "")
            ptype = proposal.get("proposal_type", "")
            proposal_id = proposal.get("id", "")
            risk = proposal.get("risk_level", "high")

            # Filter by project if requested
            if project_filter and pid != project_filter:
                continue

            # Only low-risk
            if risk != "low":
                continue

            # Only autonomy-eligible types
            if not is_autonomous_allowed_type(ptype):
                continue

            # Not already applied by autonomy engine
            if is_proposal_applied(proposal_id):
                continue

            # Risk gate check
            gate = rc.evaluate(
                proposal_id=proposal_id,
                proposal_type=ptype,
                project_id=pid,
                config=config,
            )
            if not gate.allowed:
                continue

            # Get trust score for ranking
            ts = tm.get(
                project_id=pid,
                proposal_type=ptype,
                initial_score=config.initial_trust_score,
                trust_threshold=config.trust_threshold,
                rollback_threshold=config.rollback_threshold,
            )
            candidates.append((ts.score, proposal))

        # Sort by trust score descending, then by created_at ascending (older first)
        candidates.sort(key=lambda x: (-x[0], x[1].get("created_at", "")))

        # Return top N
        return [p for _, p in candidates[:limit]]

    def evaluate_all(
        self,
        config: AutonomyConfig,
        project_filter: str = "",
    ) -> dict[str, Any]:
        """
        Evaluate all proposals and return a detailed eligibility report.

        Returns counts of eligible, ineligible, and reasons for ineligibility.
        """
        from app.apply.proposal_applier import list_proposals

        all_proposals = list_proposals()
        rc = get_risk_controller()
        tm = get_trust_manager()

        eligible: list[dict] = []
        ineligible: list[dict] = []

        for proposal in all_proposals:
            pid = proposal.get("project_id", "")
            ptype = proposal.get("proposal_type", "")
            proposal_id = proposal.get("id", "")
            risk = proposal.get("risk_level", "high")

            if project_filter and pid != project_filter:
                continue

            blocked_reasons = []

            if risk != "low":
                blocked_reasons.append(f"risk_level is '{risk}' (must be 'low')")

            if not is_autonomous_allowed_type(ptype):
                blocked_reasons.append(f"type '{ptype}' not in autonomous allowed list")

            if is_proposal_applied(proposal_id):
                blocked_reasons.append("already applied by autonomy engine")

            if not blocked_reasons:
                gate = rc.evaluate(proposal_id, ptype, pid, config)
                if not gate.allowed:
                    blocked_reasons.extend(gate.reasons_blocked)

            ts = tm.get(pid, ptype, config.initial_trust_score, config.trust_threshold, config.rollback_threshold)

            entry = {
                "proposal_id": proposal_id,
                "project_id": pid,
                "proposal_type": ptype,
                "trust_score": ts.score,
                "rollback_rate": ts.rollback_rate,
                "eligible": len(blocked_reasons) == 0,
                "blocked_reasons": blocked_reasons,
            }

            if blocked_reasons:
                ineligible.append(entry)
            else:
                eligible.append(entry)

        return {
            "total_proposals": len(all_proposals),
            "eligible_count": len(eligible),
            "ineligible_count": len(ineligible),
            "eligible": eligible,
            "ineligible": ineligible,
        }


# Module-level singleton
_selector = ProposalSelector()


def get_selector() -> ProposalSelector:
    return _selector
