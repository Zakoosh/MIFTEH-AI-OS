"""
validation.py — Pre-apply proposal validation.

Every proposal must pass validation before entering the patch/apply pipeline.
Validation is purely read-only: it never modifies files.
"""

from __future__ import annotations

from .models import Proposal, ValidationResult, RISK_LEVELS
from .safe_updates import (
    classify_risk,
    contains_forbidden_content,
    get_operation_policy,
    is_operation_allowed,
    is_safe_target_path,
)


class ProposalValidator:
    """Validates a Proposal against the safe-update policy."""

    # Only low-risk proposals may be autonomously applied
    MAX_AUTO_APPLY_RISK = "low"

    def validate(self, proposal: Proposal) -> ValidationResult:
        """Run all validation checks and return a ValidationResult."""

        checks_passed: list[str] = []
        checks_failed: list[str] = []
        warnings: list[str] = []

        # 1. Project is known
        from app.core.projects import PROJECTS
        if proposal.project_id not in PROJECTS:
            checks_failed.append(f"Unknown project_id: '{proposal.project_id}'")
        else:
            checks_passed.append("project_id recognized")

        # 2. Operation is allowed for this project
        if not is_operation_allowed(proposal.project_id, proposal.proposal_type):
            checks_failed.append(
                f"Operation '{proposal.proposal_type}' is not in the allowed list "
                f"for project '{proposal.project_id}'"
            )
        else:
            checks_passed.append("operation_type allowed")

        # 3. Target file path is safe
        path_ok, path_msg = is_safe_target_path(proposal.target_file)
        if not path_ok:
            checks_failed.append(f"Unsafe target path: {path_msg}")
        else:
            checks_passed.append("target_file path is safe")

        # 4. Changes dict is non-empty
        if not proposal.changes:
            checks_failed.append("changes dict is empty — nothing to apply")
        else:
            checks_passed.append("changes dict is non-empty")

        # 5. No forbidden content in change values
        forbidden_found = False
        for key, val in proposal.changes.items():
            bad, pattern = contains_forbidden_content(val)
            if bad:
                checks_failed.append(f"Forbidden content in field '{key}': {pattern}")
                forbidden_found = True
        if not forbidden_found and proposal.changes:
            checks_passed.append("no forbidden content in changes")

        # 6. Field length limits respected
        policy = get_operation_policy(proposal.project_id, proposal.proposal_type)
        max_len = policy.get("max_field_length", 500) if policy else 500
        length_ok = True
        for key, val in proposal.changes.items():
            if isinstance(val, str) and len(val) > max_len:
                checks_failed.append(
                    f"Field '{key}' exceeds max length {max_len} (got {len(val)})"
                )
                length_ok = False
        if length_ok and proposal.changes:
            checks_passed.append("all field lengths within limits")

        # 7. Allowed fields only (if policy defines them)
        if policy and policy.get("allowed_fields"):
            allowed = set(policy["allowed_fields"])
            extra = set(proposal.changes.keys()) - allowed
            if extra:
                warnings.append(
                    f"Fields not in policy whitelist (allowed but flagged): {sorted(extra)}"
                )
            else:
                checks_passed.append("all change keys within allowed_fields policy")

        # 8. Risk classification
        computed_risk = classify_risk(proposal.proposal_type, proposal.changes)
        risk_index = RISK_LEVELS.index(computed_risk)
        max_index = RISK_LEVELS.index(self.MAX_AUTO_APPLY_RISK)

        if risk_index > max_index:
            checks_failed.append(
                f"Computed risk '{computed_risk}' exceeds max allowed '{self.MAX_AUTO_APPLY_RISK}'"
            )
        else:
            checks_passed.append(f"risk level '{computed_risk}' is acceptable")

        # 9. Proposal ID format
        if not proposal.id or len(proposal.id) < 3:
            checks_failed.append("proposal_id is too short or missing")
        else:
            checks_passed.append("proposal_id format valid")

        # Build result
        valid = len(checks_failed) == 0
        message = (
            "Proposal is valid and eligible for apply."
            if valid
            else f"Validation failed: {checks_failed[0]}"
        )

        return ValidationResult(
            proposal_id=proposal.id,
            valid=valid,
            risk_level=computed_risk,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            warnings=warnings,
            message=message,
        )


# Module-level singleton
_validator = ProposalValidator()


def validate_proposal(proposal: Proposal) -> ValidationResult:
    """Convenience function — validates a proposal using the shared validator."""
    return _validator.validate(proposal)
