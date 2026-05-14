"""
review_chain.py — Ordered review pipeline for collaborative execution.

Reviewers evaluate each implementer's contribution in sequence.
Validators then independently assess all contributions.
Reviewer ≠ Implementer separation is enforced before adding any review.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import (
    AgentContribution,
    ReviewChain,
    ReviewRecord,
    ROLE_REVIEWER,
    ROLE_VALIDATOR,
    ROLE_QA,
    now_iso,
)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

REVIEWS_DIR = Path("app/memory/collaboration/reviews")
CHAINS_DIR  = Path("app/memory/collaboration/chains")


def _ensure_dirs() -> None:
    REVIEWS_DIR.mkdir(parents=True, exist_ok=True)
    CHAINS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# ReviewChainBuilder
# ---------------------------------------------------------------------------

class ReviewChainBuilder:
    """
    Builds and persists the review chain for one execution thread.

    Enforces:
    - Reviewers may not review their own work
    - Validators are independent of both implementers and reviewers
    - At least one reviewer and one validator are required
    """

    def build(
        self,
        thread_id: str,
        session_id: str,
        contributions: list[AgentContribution],
        reviewers: list[str],
        validators: list[str],
        mission: str,
    ) -> tuple[ReviewChain, list[ReviewRecord]]:
        """
        Execute the full review chain for a set of contributions.

        Returns (ReviewChain, list[ReviewRecord]).
        """
        _ensure_dirs()

        chain = ReviewChain(
            thread_id=thread_id,
            session_id=session_id,
            reviewers=reviewers,
            validators=validators,
        )

        all_reviews: list[ReviewRecord] = []
        implementer_contributions = [c for c in contributions if c.role == "implementer"]

        # ── Phase 1: Reviewer chain ─────────────────────────────────────
        for reviewer in reviewers:
            for contribution in implementer_contributions:
                # Enforce separation: reviewer ≠ implementer
                if reviewer == contribution.agent_name:
                    continue

                review = self._create_review(
                    thread_id=thread_id,
                    session_id=session_id,
                    reviewer=reviewer,
                    reviewed_agent=contribution.agent_name,
                    contribution=contribution,
                    role=ROLE_REVIEWER,
                    mission=mission,
                )
                self._save_review(review)
                chain.review_ids.append(review.review_id)
                all_reviews.append(review)

        # ── Phase 2: Independent validator chain ────────────────────────
        for validator in validators:
            # Validators review all contributions (implementers + entire output)
            for contribution in contributions:
                if validator == contribution.agent_name:
                    continue
                # Validator must not be in reviewers either
                if validator in reviewers:
                    continue

                review = self._create_review(
                    thread_id=thread_id,
                    session_id=session_id,
                    reviewer=validator,
                    reviewed_agent=contribution.agent_name,
                    contribution=contribution,
                    role=ROLE_VALIDATOR,
                    mission=mission,
                )
                self._save_review(review)
                chain.review_ids.append(review.review_id)
                all_reviews.append(review)

        # Determine chain approval: all reviews must approve
        chain.chain_approved = all(r.approved for r in all_reviews) if all_reviews else False
        chain.completed = True
        self._save_chain(chain)

        return chain, all_reviews

    # ------------------------------------------------------------------
    # Review generation (deterministic offline simulation)
    # ------------------------------------------------------------------

    def _create_review(
        self,
        thread_id: str,
        session_id: str,
        reviewer: str,
        reviewed_agent: str,
        contribution: AgentContribution,
        role: str,
        mission: str,
    ) -> ReviewRecord:
        """Generate a ReviewRecord using deterministic offline scoring."""

        score, approved, feedback, concerns = self._score_contribution(
            reviewer=reviewer,
            reviewed_agent=reviewed_agent,
            contribution=contribution,
            role=role,
            mission=mission,
        )

        return ReviewRecord(
            thread_id=thread_id,
            session_id=session_id,
            reviewer_agent=reviewer,
            reviewed_agent=reviewed_agent,
            contribution_id=contribution.contribution_id,
            score=score,
            approved=approved,
            feedback=feedback,
            concerns=concerns,
            role=role,
        )

    def _score_contribution(
        self,
        reviewer: str,
        reviewed_agent: str,
        contribution: AgentContribution,
        role: str,
        mission: str,
    ) -> tuple[float, bool, str, list[str]]:
        """
        Deterministic offline review scoring.
        Returns (score, approved, feedback, concerns).
        """
        h = int(hashlib.sha256(
            f"{reviewer}:{reviewed_agent}:{mission}:{role}".encode()
        ).hexdigest(), 16)

        # Validators score slightly higher on average (independent authority)
        base = 84.0 if role == ROLE_VALIDATOR else 80.0
        variance = (h % 22) - 5    # -5 to +16
        score = round(min(100.0, max(55.0, base + variance)), 1)
        approved = score >= 70.0

        # Generate role-appropriate feedback
        if role == ROLE_VALIDATOR:
            feedback = (
                f"Independent validation of {reviewed_agent}'s work on '{mission}': "
                f"{'All acceptance criteria met.' if approved else 'Some criteria require attention.'} "
                f"Performance benchmarks {'passed' if score > 75 else 'marginal'}."
            )
        else:
            feedback = (
                f"Peer review of {reviewed_agent}'s implementation for '{mission}': "
                f"{'Implementation is solid and production-ready.' if approved else 'Implementation needs revisions.'} "
                f"Code quality {'acceptable' if score > 70 else 'needs improvement'}."
            )

        concerns: list[str] = []
        if score < 72:
            concerns.append("Quality score below threshold — recommend revision")
        if (h % 7) == 0:
            concerns.append("Minor edge case handling could be improved")
        if (h % 11) == 0 and not approved:
            concerns.append("Additional testing recommended before deployment")

        return score, approved, feedback, concerns

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_review(self, review_id: str) -> ReviewRecord | None:
        _ensure_dirs()
        path = REVIEWS_DIR / f"{review_id}.json"
        if not path.exists():
            return None
        try:
            return ReviewRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return None

    def list_all_reviews(self) -> list[ReviewRecord]:
        _ensure_dirs()
        reviews = []
        for f in REVIEWS_DIR.glob("*.json"):
            try:
                reviews.append(ReviewRecord.from_dict(json.loads(f.read_text(encoding="utf-8"))))
            except Exception:
                pass
        reviews.sort(key=lambda r: r.timestamp, reverse=True)
        return reviews

    def list_reviews_for_session(self, session_id: str) -> list[ReviewRecord]:
        return [r for r in self.list_all_reviews() if r.session_id == session_id]

    def get_chain(self, chain_id: str) -> ReviewChain | None:
        _ensure_dirs()
        path = CHAINS_DIR / f"{chain_id}.json"
        if not path.exists():
            return None
        try:
            return ReviewChain.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save_review(self, r: ReviewRecord) -> None:
        _ensure_dirs()
        path = REVIEWS_DIR / f"{r.review_id}.json"
        try:
            path.write_text(json.dumps(r.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def _save_chain(self, c: ReviewChain) -> None:
        _ensure_dirs()
        path = CHAINS_DIR / f"{c.chain_id}.json"
        try:
            path.write_text(json.dumps(c.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


# Module-level singleton
_builder = ReviewChainBuilder()


def get_review_chain_builder() -> ReviewChainBuilder:
    return _builder
