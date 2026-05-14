"""
consensus.py — Consensus scoring aggregation for collaborative sessions.

Aggregates individual review scores from reviewers and validators into a
single weighted consensus score. Validators carry higher weight than reviewers
to reflect their independent authority.

Approved = consensus_score >= threshold (default 75).
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import ConsensusScore, ReviewRecord, ROLE_VALIDATOR, ROLE_QA, now_iso


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

CONSENSUS_DIR = Path("app/memory/collaboration/consensus")


def _ensure_dirs() -> None:
    CONSENSUS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Weight policy
# ---------------------------------------------------------------------------

# Role → scoring weight multiplier
ROLE_WEIGHTS: dict[str, float] = {
    ROLE_VALIDATOR: 1.40,   # highest authority — independent
    ROLE_QA:        1.25,
    "reviewer":     1.00,   # standard peer review
}

DEFAULT_WEIGHT = 1.00
APPROVAL_THRESHOLD = 75.0          # consensus_score >= this → approved
DIVERGENCE_THRESHOLD = 25.0        # score_spread > this → flag as divergent


# ---------------------------------------------------------------------------
# ConsensusEngine
# ---------------------------------------------------------------------------

class ConsensusEngine:
    """
    Computes and persists a ConsensusScore from a list of ReviewRecords.

    Algorithm:
      1. Collect each reviewer/validator's score
      2. Assign weight by role (validators > reviewers)
      3. Compute weighted average
      4. Round to one decimal place
      5. Approve if weighted_avg >= threshold
    """

    def compute(
        self,
        session_id: str,
        thread_id: str,
        reviews: list[ReviewRecord],
        threshold: float = APPROVAL_THRESHOLD,
    ) -> ConsensusScore:
        """Aggregate review scores into a ConsensusScore and persist it."""
        _ensure_dirs()

        # Deduplicate: one score per reviewer (take the highest if multiple reviews)
        best_per_reviewer: dict[str, ReviewRecord] = {}
        for review in reviews:
            key = review.reviewer_agent
            if key not in best_per_reviewer or review.score > best_per_reviewer[key].score:
                best_per_reviewer[key] = review

        individual_scores: dict[str, float] = {}
        role_weights: dict[str, float] = {}
        abstentions: list[str] = []

        for agent, review in best_per_reviewer.items():
            individual_scores[agent] = review.score
            role_weights[agent] = ROLE_WEIGHTS.get(review.role, DEFAULT_WEIGHT)

        # Weighted average
        if individual_scores:
            total_weight = sum(role_weights[a] for a in individual_scores)
            weighted_sum = sum(
                individual_scores[a] * role_weights[a]
                for a in individual_scores
            )
            weighted_avg = weighted_sum / total_weight if total_weight > 0 else 0.0
        else:
            weighted_avg = 0.0
            abstentions = ["no_reviews"]

        consensus_score = round(weighted_avg, 1)
        approved = consensus_score >= threshold

        # Divergence check
        scores_list = list(individual_scores.values())
        spread = round(max(scores_list) - min(scores_list), 1) if len(scores_list) > 1 else 0.0

        result = ConsensusScore(
            session_id=session_id,
            thread_id=thread_id,
            individual_scores=individual_scores,
            role_weights=role_weights,
            weighted_score=round(weighted_avg, 2),
            consensus_score=consensus_score,
            approved=approved,
            threshold=threshold,
            abstentions=abstentions,
            score_spread=spread,
        )

        self._save(result)
        return result

    def get_consensus(self, consensus_id: str) -> ConsensusScore | None:
        _ensure_dirs()
        path = CONSENSUS_DIR / f"{consensus_id}.json"
        if not path.exists():
            return None
        try:
            return ConsensusScore.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            return None

    def list_all(self) -> list[ConsensusScore]:
        _ensure_dirs()
        results = []
        for f in CONSENSUS_DIR.glob("*.json"):
            try:
                results.append(ConsensusScore.from_dict(json.loads(f.read_text(encoding="utf-8"))))
            except Exception:
                pass
        results.sort(key=lambda c: c.timestamp, reverse=True)
        return results

    def analytics(self) -> dict:
        """Return aggregate consensus analytics."""
        all_cs = self.list_all()
        if not all_cs:
            return {
                "total": 0, "approved": 0, "rejected": 0,
                "avg_consensus_score": 0.0, "avg_spread": 0.0,
                "approval_rate": 0.0,
            }
        approved = sum(1 for c in all_cs if c.approved)
        avg_score = round(sum(c.consensus_score for c in all_cs) / len(all_cs), 1)
        avg_spread = round(sum(c.score_spread for c in all_cs) / len(all_cs), 1)
        return {
            "total": len(all_cs),
            "approved": approved,
            "rejected": len(all_cs) - approved,
            "avg_consensus_score": avg_score,
            "avg_spread": avg_spread,
            "approval_rate": round(approved / len(all_cs) * 100, 1),
        }

    def _save(self, cs: ConsensusScore) -> None:
        path = CONSENSUS_DIR / f"{cs.consensus_id}.json"
        try:
            path.write_text(json.dumps(cs.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass


# Module-level singleton
_engine = ConsensusEngine()


def get_consensus_engine() -> ConsensusEngine:
    return _engine
