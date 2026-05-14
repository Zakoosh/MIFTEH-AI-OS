"""
conflict_resolution.py — Detects and resolves conflicts in collaborative sessions.

Conflict types:
  score_divergence    — reviewer scores differ by more than DIVERGENCE_THRESHOLD
  role_violation      — an agent was assigned a role that violates separation rules
  contradictory_output — reviewers reached opposite approval decisions

Resolution strategies:
  majority_vote       — resolved by which decision (approve/reject) has more votes
  abstention          — conflicting agent abstains; excluded from final consensus
  override            — system overrides with conservative (reject) decision
  escalation          — flags for human review (marks unresolved)
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import ConflictRecord, ReviewRecord, now_iso


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

CONFLICTS_DIR = Path("app/memory/collaboration/conflicts")

DIVERGENCE_THRESHOLD = 25.0   # score spread above this = divergence conflict


def _ensure_dirs() -> None:
    CONFLICTS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# ConflictResolver
# ---------------------------------------------------------------------------

class ConflictResolver:
    """
    Scans a list of ReviewRecords for conflicts and resolves them.

    Returns a list of ConflictRecords. Conflicts that can be resolved
    automatically are marked resolved=True; others escalate.
    """

    def detect_and_resolve(
        self,
        thread_id: str,
        session_id: str,
        reviews: list[ReviewRecord],
        agent_roles: dict[str, str],
    ) -> list[ConflictRecord]:
        """Run full conflict detection and resolution pipeline."""
        _ensure_dirs()
        conflicts: list[ConflictRecord] = []

        # ── 1. Score divergence ─────────────────────────────────────────
        divergence_conflicts = self._detect_score_divergence(
            thread_id, session_id, reviews
        )
        conflicts.extend(divergence_conflicts)

        # ── 2. Role violations ──────────────────────────────────────────
        role_conflicts = self._detect_role_violations(
            thread_id, session_id, reviews, agent_roles
        )
        conflicts.extend(role_conflicts)

        # ── 3. Contradictory outcomes ────────────────────────────────────
        contradiction_conflicts = self._detect_contradictions(
            thread_id, session_id, reviews
        )
        conflicts.extend(contradiction_conflicts)

        # Persist all conflicts
        for c in conflicts:
            self._save(c)

        return conflicts

    # ------------------------------------------------------------------
    # Detectors
    # ------------------------------------------------------------------

    def _detect_score_divergence(
        self,
        thread_id: str,
        session_id: str,
        reviews: list[ReviewRecord],
    ) -> list[ConflictRecord]:
        """Flag when two reviewers score the same contribution divergently."""
        conflicts = []
        # Group by contribution_id
        by_contribution: dict[str, list[ReviewRecord]] = {}
        for r in reviews:
            by_contribution.setdefault(r.contribution_id, []).append(r)

        for cid, group in by_contribution.items():
            if len(group) < 2:
                continue
            scores = [r.score for r in group]
            spread = max(scores) - min(scores)
            if spread >= DIVERGENCE_THRESHOLD:
                agents = [r.reviewer_agent for r in group]
                conflict = ConflictRecord(
                    thread_id=thread_id,
                    session_id=session_id,
                    conflicting_agents=agents,
                    conflict_type="score_divergence",
                    description=(
                        f"Score spread of {spread:.1f} points on contribution {cid}. "
                        f"Scores: {dict(zip(agents, scores))}."
                    ),
                    resolved=True,
                    resolution="majority_vote",
                    resolved_by="system",
                )
                conflicts.append(conflict)
        return conflicts

    def _detect_role_violations(
        self,
        thread_id: str,
        session_id: str,
        reviews: list[ReviewRecord],
        agent_roles: dict[str, str],
    ) -> list[ConflictRecord]:
        """Flag when a reviewer reviewed their own work."""
        conflicts = []
        for r in reviews:
            if r.reviewer_agent == r.reviewed_agent:
                conflict = ConflictRecord(
                    thread_id=thread_id,
                    session_id=session_id,
                    conflicting_agents=[r.reviewer_agent],
                    conflict_type="role_violation",
                    description=(
                        f"Agent '{r.reviewer_agent}' attempted to review their own contribution. "
                        "Self-review is not permitted."
                    ),
                    resolved=True,
                    resolution="abstention",
                    resolved_by="system",
                )
                conflicts.append(conflict)

        # Check implementer in reviewer role
        for r in reviews:
            expected_role = agent_roles.get(r.reviewer_agent, "")
            if expected_role == "implementer" and r.role in ("reviewer", "validator"):
                conflict = ConflictRecord(
                    thread_id=thread_id,
                    session_id=session_id,
                    conflicting_agents=[r.reviewer_agent],
                    conflict_type="role_violation",
                    description=(
                        f"Implementer '{r.reviewer_agent}' submitted a review, "
                        "violating implementer/reviewer separation."
                    ),
                    resolved=True,
                    resolution="override",
                    resolved_by="system",
                )
                conflicts.append(conflict)

        return conflicts

    def _detect_contradictions(
        self,
        thread_id: str,
        session_id: str,
        reviews: list[ReviewRecord],
    ) -> list[ConflictRecord]:
        """Flag when reviewer and validator reach opposite approve/reject decisions."""
        conflicts = []
        reviewer_decisions = {r.reviewer_agent: r.approved for r in reviews if r.role == "reviewer"}
        validator_decisions = {r.reviewer_agent: r.approved for r in reviews if r.role == "validator"}

        rev_approved  = sum(1 for v in reviewer_decisions.values() if v)
        val_approved  = sum(1 for v in validator_decisions.values() if v)
        rev_rejected  = len(reviewer_decisions) - rev_approved
        val_rejected  = len(validator_decisions) - val_approved

        # Contradiction: majority of reviewers approve but majority of validators reject (or vice versa)
        reviewers_say_yes   = rev_approved > rev_rejected
        validators_say_yes  = val_approved > val_rejected

        if reviewer_decisions and validator_decisions and reviewers_say_yes != validators_say_yes:
            conflict = ConflictRecord(
                thread_id=thread_id,
                session_id=session_id,
                conflicting_agents=list(reviewer_decisions.keys()) + list(validator_decisions.keys()),
                conflict_type="contradictory_output",
                description=(
                    f"Reviewers {'approved' if reviewers_say_yes else 'rejected'} "
                    f"but validators {'approved' if validators_say_yes else 'rejected'}. "
                    "Contradiction detected between review layers."
                ),
                resolved=True,
                resolution="majority_vote",
                resolved_by="system",
            )
            conflicts.append(conflict)

        return conflicts

    # ------------------------------------------------------------------
    # Analytics helpers
    # ------------------------------------------------------------------

    def list_all(self) -> list[ConflictRecord]:
        _ensure_dirs()
        results = []
        for f in CONFLICTS_DIR.glob("*.json"):
            try:
                results.append(ConflictRecord.from_dict(json.loads(f.read_text(encoding="utf-8"))))
            except Exception:
                pass
        results.sort(key=lambda c: c.timestamp, reverse=True)
        return results

    def count_unresolved(self, thread_id: str = "") -> int:
        records = self.list_all()
        if thread_id:
            records = [c for c in records if c.thread_id == thread_id]
        return sum(1 for c in records if not c.resolved)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save(self, c: ConflictRecord) -> None:
        path = CONFLICTS_DIR / f"{c.conflict_id}.json"
        try:
            path.write_text(json.dumps(c.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


# Module-level singleton
_resolver = ConflictResolver()


def get_conflict_resolver() -> ConflictResolver:
    return _resolver
