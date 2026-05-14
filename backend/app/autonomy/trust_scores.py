"""
trust_scores.py — Trust score management for the Autonomous Operational Loops Layer.

Each (project_id, proposal_type) pair has an independent trust score.
Trust scores persist to disk and survive restarts.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import TrustScore, now_iso


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

TRUST_DIR = Path("app/memory/autonomy/trust")


def _ensure_dirs() -> None:
    TRUST_DIR.mkdir(parents=True, exist_ok=True)


def _score_file(project_id: str, proposal_type: str) -> Path:
    safe = lambda s: s.replace(":", "_").replace("/", "_")
    return TRUST_DIR / f"{safe(project_id)}_{safe(proposal_type)}.json"


# ---------------------------------------------------------------------------
# TrustScoreManager
# ---------------------------------------------------------------------------

class TrustScoreManager:
    """
    Manages trust scores for all (project_id, proposal_type) pairs.

    Trust score rules:
      - Initial score: config.initial_trust_score (default 80)
      - Success: +config.trust_gain_on_success (default +2, capped at 100)
      - Failure: -config.trust_loss_on_failure (default -10, floored at 0)
      - Rollback: -config.trust_loss_on_failure (same penalty)
      - Suspension: when rollback_rate > rollback_threshold
      - Reinstatement: manual or when score > reinstate_threshold
    """

    def get(
        self,
        project_id: str,
        proposal_type: str,
        initial_score: float = 80.0,
        trust_threshold: float = 75.0,
        rollback_threshold: float = 20.0,
    ) -> TrustScore:
        """Load existing trust score or create a fresh one."""
        _ensure_dirs()
        path = _score_file(project_id, proposal_type)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                ts = TrustScore.from_dict(data)
                # Recompute derived fields
                ts.autonomous_apply_allowed = (
                    ts.score >= trust_threshold
                    and ts.rollback_rate <= rollback_threshold
                    and not ts.suspended
                )
                return ts
            except Exception:
                pass

        # Create new
        key = f"{project_id}:{proposal_type}"
        ts = TrustScore(
            key=key,
            project_id=project_id,
            proposal_type=proposal_type,
            score=initial_score,
            autonomous_apply_allowed=initial_score >= trust_threshold,
        )
        self._save(ts)
        return ts

    def apply_success(
        self,
        project_id: str,
        proposal_type: str,
        gain: float = 2.0,
        trust_threshold: float = 75.0,
        rollback_threshold: float = 20.0,
        initial_score: float = 80.0,
    ) -> tuple[TrustScore, float, float]:
        """Apply a success outcome. Returns (updated_ts, old_score, new_score)."""
        ts = self.get(project_id, proposal_type, initial_score, trust_threshold, rollback_threshold)
        old_score = ts.score
        ts.score = min(100.0, round(ts.score + gain, 2))
        ts.apply_count += 1
        ts.success_count += 1
        ts.recompute()
        ts.autonomous_apply_allowed = (
            ts.score >= trust_threshold
            and ts.rollback_rate <= rollback_threshold
            and not ts.suspended
        )
        self._save(ts)
        return ts, old_score, ts.score

    def apply_failure(
        self,
        project_id: str,
        proposal_type: str,
        loss: float = 10.0,
        rollback: bool = False,
        trust_threshold: float = 75.0,
        rollback_threshold: float = 20.0,
        suspension_threshold: int = 3,
        initial_score: float = 80.0,
    ) -> tuple[TrustScore, float, float]:
        """Apply a failure or rollback outcome. Returns (updated_ts, old_score, new_score)."""
        ts = self.get(project_id, proposal_type, initial_score, trust_threshold, rollback_threshold)
        old_score = ts.score
        ts.score = max(0.0, round(ts.score - loss, 2))
        ts.apply_count += 1
        ts.failure_count += 1
        if rollback:
            ts.rollback_count += 1
        ts.recompute()

        # Check suspension threshold
        if ts.rollback_rate > rollback_threshold and not ts.suspended:
            ts.suspended = True
            ts.suspension_reason = (
                f"Rollback rate {ts.rollback_rate:.1f}% exceeds threshold {rollback_threshold:.1f}%"
            )

        ts.autonomous_apply_allowed = (
            ts.score >= trust_threshold
            and ts.rollback_rate <= rollback_threshold
            and not ts.suspended
        )
        self._save(ts)
        return ts, old_score, ts.score

    def reinstate(
        self,
        project_id: str,
        proposal_type: str,
        reinstate_threshold: float = 60.0,
        initial_score: float = 80.0,
        trust_threshold: float = 75.0,
        rollback_threshold: float = 20.0,
    ) -> TrustScore:
        """Reinstate a suspended trust score if eligible."""
        ts = self.get(project_id, proposal_type, initial_score, trust_threshold, rollback_threshold)
        if ts.suspended and ts.score >= reinstate_threshold:
            ts.suspended = False
            ts.suspension_reason = ""
            ts.autonomous_apply_allowed = (
                ts.score >= trust_threshold
                and ts.rollback_rate <= rollback_threshold
            )
            self._save(ts)
        return ts

    def list_all(
        self,
        trust_threshold: float = 75.0,
        rollback_threshold: float = 20.0,
    ) -> list[TrustScore]:
        """Return all persisted trust scores."""
        _ensure_dirs()
        scores = []
        for file in TRUST_DIR.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                ts = TrustScore.from_dict(data)
                ts.autonomous_apply_allowed = (
                    ts.score >= trust_threshold
                    and ts.rollback_rate <= rollback_threshold
                    and not ts.suspended
                )
                scores.append(ts)
            except Exception:
                pass
        scores.sort(key=lambda x: x.score, reverse=True)
        return scores

    def get_score_for_type(
        self,
        project_id: str,
        proposal_type: str,
        initial_score: float = 80.0,
        trust_threshold: float = 75.0,
        rollback_threshold: float = 20.0,
    ) -> float:
        """Convenience: return just the numeric score."""
        ts = self.get(project_id, proposal_type, initial_score, trust_threshold, rollback_threshold)
        return ts.score

    def seed_defaults(
        self,
        initial_score: float = 80.0,
        trust_threshold: float = 75.0,
        rollback_threshold: float = 20.0,
    ) -> None:
        """Seed default trust scores for all known proposal types."""
        known = [
            ("yallaplays", "seo"),
            ("yallaplays", "landing_page"),
            ("yallaplays", "category"),
            ("yallaplays", "manifest"),
            ("yallaplays", "metadata"),
            ("fionera", "dashboard"),
            ("fionera", "widget"),
            ("fionera", "watchlist"),
            ("fionera", "metadata"),
            ("fionera", "seo"),
        ]
        for project_id, proposal_type in known:
            path = _score_file(project_id, proposal_type)
            if not path.exists():
                self.get(project_id, proposal_type, initial_score, trust_threshold, rollback_threshold)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _save(self, ts: TrustScore) -> None:
        _ensure_dirs()
        path = _score_file(ts.project_id, ts.proposal_type)
        try:
            path.write_text(
                json.dumps(ts.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass


# Module-level singleton
_manager = TrustScoreManager()


def get_trust_manager() -> TrustScoreManager:
    return _manager
