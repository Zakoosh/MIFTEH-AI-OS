"""
collaboration_memory.py — Persistent memory for the Collaboration Layer.

Stores and retrieves collaboration sessions, threads, reviews, and
consensus scores. Provides analytics aggregation for the dashboard.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import CollaborationSession, now_iso


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

SESSIONS_DIR = Path("app/memory/collaboration/sessions")


def _ensure_dirs() -> None:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# CollaborationMemory
# ---------------------------------------------------------------------------

class CollaborationMemory:
    """
    Persists and retrieves CollaborationSession records.

    Other sub-objects (threads, reviews, consensus, quality) are
    persisted by their own managers; this class aggregates them.
    """

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    def save_session(self, session: CollaborationSession) -> None:
        _ensure_dirs()
        path = SESSIONS_DIR / f"{session.session_id}.json"
        try:
            path.write_text(
                json.dumps(session.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def get_session(self, session_id: str) -> CollaborationSession | None:
        _ensure_dirs()
        path = SESSIONS_DIR / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            return CollaborationSession.from_dict(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except Exception:
            return None

    def list_sessions(self) -> list[CollaborationSession]:
        _ensure_dirs()
        sessions = []
        for f in SESSIONS_DIR.glob("*.json"):
            try:
                sessions.append(
                    CollaborationSession.from_dict(json.loads(f.read_text(encoding="utf-8")))
                )
            except Exception:
                pass
        sessions.sort(key=lambda s: s.started_at, reverse=True)
        return sessions

    def list_sessions_as_dicts(self) -> list[dict]:
        return [s.to_dict() for s in self.list_sessions()]

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def session_metrics(self) -> dict[str, Any]:
        """Aggregate metrics across all collaboration sessions."""
        sessions = self.list_sessions()
        total = len(sessions)
        if total == 0:
            return {
                "total_sessions": 0,
                "approved": 0, "rejected": 0, "running": 0,
                "avg_consensus_score": 0.0,
                "avg_quality_score": 0.0,
                "approval_rate": 0.0,
                "total_agents_deployed": 0,
                "unique_missions": [],
            }

        approved     = sum(1 for s in sessions if s.approved)
        rejected     = sum(1 for s in sessions if not s.approved and s.status != "running")
        running      = sum(1 for s in sessions if s.status == "running")
        avg_consensus = round(sum(s.consensus_score for s in sessions) / total, 1) if total else 0.0
        avg_quality   = round(sum(s.quality_score for s in sessions) / total, 1) if total else 0.0
        total_agents  = sum(len(s.agents) for s in sessions)
        missions      = sorted({s.mission for s in sessions})

        return {
            "total_sessions":      total,
            "approved":            approved,
            "rejected":            rejected,
            "running":             running,
            "avg_consensus_score": avg_consensus,
            "avg_quality_score":   avg_quality,
            "approval_rate":       round(approved / total * 100, 1) if total else 0.0,
            "total_agents_deployed": total_agents,
            "unique_missions":     missions,
        }

    def mission_breakdown(self) -> dict[str, dict]:
        """Break down sessions per mission type."""
        sessions = self.list_sessions()
        breakdown: dict[str, dict] = {}
        for s in sessions:
            m = s.mission
            if m not in breakdown:
                breakdown[m] = {"total": 0, "approved": 0, "avg_consensus": 0.0, "scores": []}
            breakdown[m]["total"] += 1
            if s.approved:
                breakdown[m]["approved"] += 1
            breakdown[m]["scores"].append(s.consensus_score)

        for m, data in breakdown.items():
            scores = data.pop("scores")
            data["avg_consensus"] = round(sum(scores) / len(scores), 1) if scores else 0.0
            data["approval_rate"] = round(data["approved"] / data["total"] * 100, 1)

        return breakdown

    def agent_activity(self) -> dict[str, dict]:
        """Count how often each agent appeared across sessions."""
        sessions = self.list_sessions()
        activity: dict[str, dict] = {}
        for s in sessions:
            for agent in s.agents:
                if agent not in activity:
                    activity[agent] = {"sessions": 0, "approved": 0}
                activity[agent]["sessions"] += 1
                if s.approved:
                    activity[agent]["approved"] += 1
        # Sort by activity count
        return dict(sorted(activity.items(), key=lambda x: x[1]["sessions"], reverse=True))

    def generate_insights(self, sessions: list[CollaborationSession]) -> list[str]:
        """Generate operational insights from session history."""
        insights = []
        if not sessions:
            insights.append("No collaboration sessions recorded yet. Run the first session to begin.")
            return insights

        total = len(sessions)
        approved = sum(1 for s in sessions if s.approved)
        approval_rate = round(approved / total * 100, 1)

        insights.append(
            f"{total} collaboration session(s) recorded. "
            f"Approval rate: {approval_rate}% ({approved}/{total} approved)."
        )

        avg_consensus = round(sum(s.consensus_score for s in sessions) / total, 1)
        insights.append(f"Average consensus score across all sessions: {avg_consensus}/100.")

        missions = {s.mission for s in sessions}
        insights.append(f"Active collaboration missions: {', '.join(sorted(missions))}.")

        low_consensus = [s for s in sessions if s.consensus_score < 70]
        if low_consensus:
            low_missions = {s.mission for s in low_consensus}
            insights.append(
                f"ALERT: {len(low_consensus)} session(s) with consensus < 70 "
                f"in missions: {', '.join(sorted(low_missions))}."
            )

        conflicts_total = sum(s.conflicts_detected for s in sessions)
        if conflicts_total > 0:
            resolved = sum(s.conflicts_resolved for s in sessions)
            insights.append(
                f"{conflicts_total} conflict(s) detected, {resolved} auto-resolved."
            )
        else:
            insights.append("Zero conflicts detected — collaboration quality is high.")

        return insights


# Module-level singleton
_memory = CollaborationMemory()


def get_collaboration_memory() -> CollaborationMemory:
    return _memory
