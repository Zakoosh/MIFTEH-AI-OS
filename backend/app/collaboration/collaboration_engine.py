"""
collaboration_engine.py — Core orchestrator for the Multi-Agent Collaborative Execution Layer.

Execution flow per session:
  Proposal Selection / Mission Input
  → Task Distribution (role assignment, separation check)
  → Execution Threads (each agent contributes)
  → Review Chain (reviewers evaluate implementers)
  → Consensus Scoring (weighted aggregate)
  → Conflict Detection & Resolution
  → Quality Control
  → Session Completion
  → Memory Persistence

Safety guarantees:
  - Reviewer ≠ Implementer (always enforced)
  - Validator independence (always enforced)
  - No single-agent unsafe overwrite
  - Full audit trail in collaboration memory
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    CollaborationSession,
    ExecutionThread,
    SESSION_RUNNING,
    SESSION_APPROVED,
    SESSION_REJECTED,
    THREAD_RUNNING,
    THREAD_REVIEW,
    THREAD_CONSENSUS,
    now_iso,
)
from .agent_roles import get_mission, build_role_map, get_all_agents_for_mission
from .task_distribution import get_distributor
from .execution_threads import get_thread_manager
from .review_chain import get_review_chain_builder
from .consensus import get_consensus_engine
from .quality_control import get_quality_controller
from .conflict_resolution import get_conflict_resolver
from .collaboration_memory import get_collaboration_memory


# ---------------------------------------------------------------------------
# CollaborationEngine
# ---------------------------------------------------------------------------

class CollaborationEngine:
    """
    Orchestrates full multi-agent collaborative execution sessions.

    Each call to run_session() produces a complete CollaborationSession
    with threads, contributions, reviews, consensus, QC, and conflicts.
    """

    def __init__(self) -> None:
        self._distributor = get_distributor()
        self._threads     = get_thread_manager()
        self._review_chain = get_review_chain_builder()
        self._consensus   = get_consensus_engine()
        self._qc          = get_quality_controller()
        self._conflicts   = get_conflict_resolver()
        self._memory      = get_collaboration_memory()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run_session(
        self,
        mission: str,
        project_id: str = "",
        proposal_id: str = "",
        proposal_title: str = "",
        triggered_by: str = "api",
        consensus_threshold: float = 75.0,
        dry_run: bool = False,
    ) -> CollaborationSession:
        """
        Execute a full collaborative session for the given mission.

        Returns a completed CollaborationSession.
        """

        # ── Create session ──────────────────────────────────────────────
        session = CollaborationSession(
            mission=mission,
            proposal_id=proposal_id,
            project_id=project_id,
            triggered_by=triggered_by,
            status=SESSION_RUNNING,
        )
        self._memory.save_session(session)

        try:
            result = self._execute(
                session=session,
                mission=mission,
                project_id=project_id,
                proposal_id=proposal_id,
                proposal_title=proposal_title,
                consensus_threshold=consensus_threshold,
                dry_run=dry_run,
            )
        except Exception as exc:
            session.status = SESSION_REJECTED
            session.summary = f"Session aborted: {exc}"
            session.completed_at = now_iso()
            self._memory.save_session(session)
            return session

        return result

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    def _execute(
        self,
        session: CollaborationSession,
        mission: str,
        project_id: str,
        proposal_id: str,
        proposal_title: str,
        consensus_threshold: float,
        dry_run: bool,
    ) -> CollaborationSession:
        """Full pipeline: distribute → execute → review → consensus → QC."""

        # ── 1. Task distribution ────────────────────────────────────────
        distribution = self._distributor.distribute(
            mission=mission,
            proposal_id=proposal_id,
            proposal_title=proposal_title or mission,
            project_id=project_id,
        )

        # Validate role separation
        sep_ok, violations = self._distributor.validate_separation(
            distribution["implementers"],
            distribution["reviewers"],
            distribution["validators"],
        )
        if not sep_ok:
            session.status = SESSION_REJECTED
            session.summary = f"Role separation violated: {violations}"
            session.completed_at = now_iso()
            self._memory.save_session(session)
            return session

        session.agents     = distribution["all_agents"]
        session.agent_roles = distribution["agent_roles"]
        self._memory.save_session(session)

        # ── 2. Create execution thread ──────────────────────────────────
        thread = self._threads.create(
            session_id=session.session_id,
            mission=mission,
            proposal_id=proposal_id,
            project_id=project_id,
            agent_roles=distribution["agent_roles"],
        )
        session.thread_ids.append(thread.thread_id)
        self._memory.save_session(session)

        # ── 3. Run implementer agents ───────────────────────────────────
        self._threads.advance(thread, THREAD_RUNNING)
        for assignment in distribution["task_assignments"]:
            if assignment["role"] == "implementer":
                self._threads.execute_agent(
                    thread=thread,
                    agent_name=assignment["agent_name"],
                    role=assignment["role"],
                    task=assignment["task"],
                    session_id=session.session_id,
                )

        # ── 4. Review chain ─────────────────────────────────────────────
        self._threads.advance(thread, THREAD_REVIEW)
        contributions = self._threads.get_contributions_for_thread(thread)

        chain, reviews = self._review_chain.build(
            thread_id=thread.thread_id,
            session_id=session.session_id,
            contributions=contributions,
            reviewers=distribution["reviewers"],
            validators=distribution["validators"],
            mission=mission,
        )

        thread.review_ids = chain.review_ids
        thread.chain_id   = chain.chain_id

        # Also execute reviewer + validator agents (for contribution records)
        for assignment in distribution["task_assignments"]:
            if assignment["role"] in ("reviewer", "validator"):
                self._threads.execute_agent(
                    thread=thread,
                    agent_name=assignment["agent_name"],
                    role=assignment["role"],
                    task=assignment["task"],
                    session_id=session.session_id,
                )

        # ── 5. Consensus scoring ────────────────────────────────────────
        self._threads.advance(thread, THREAD_CONSENSUS)
        consensus = self._consensus.compute(
            session_id=session.session_id,
            thread_id=thread.thread_id,
            reviews=reviews,
            threshold=consensus_threshold,
        )

        # ── 6. Conflict detection & resolution ──────────────────────────
        conflicts = self._conflicts.detect_and_resolve(
            thread_id=thread.thread_id,
            session_id=session.session_id,
            reviews=reviews,
            agent_roles=distribution["agent_roles"],
        )
        thread.conflicts = len(conflicts)
        unresolved = sum(1 for c in conflicts if not c.resolved)

        # ── 7. Quality control ──────────────────────────────────────────
        qc_report = self._qc.run(
            thread=thread,
            reviews=reviews,
            consensus=consensus,
            unresolved_conflicts=unresolved,
        )

        # ── 8. Complete thread ──────────────────────────────────────────
        final_approved = consensus.approved and qc_report.approved
        self._threads.complete(
            thread=thread,
            approved=final_approved,
            consensus_score=consensus.consensus_score,
            quality_score=qc_report.quality_score,
        )

        # ── 9. Complete session ─────────────────────────────────────────
        reviewed_by = list({r.reviewer_agent for r in reviews})
        session.consensus_score   = consensus.consensus_score
        session.approved          = final_approved
        session.review_status     = "approved" if final_approved else "rejected"
        session.reviewed_by       = reviewed_by
        session.quality_score     = qc_report.quality_score
        session.conflicts_detected = len(conflicts)
        session.conflicts_resolved = len([c for c in conflicts if c.resolved])
        session.complete(approved=final_approved)

        # Generate insights
        session.insights = self._build_insights(
            session=session,
            distribution=distribution,
            consensus=consensus,
            qc_report=qc_report,
            conflicts=conflicts,
        )

        session.summary = (
            f"Mission '{mission}' — {len(session.agents)} agents, "
            f"consensus {consensus.consensus_score}, "
            f"{'approved' if final_approved else 'rejected'}."
        )

        self._memory.save_session(session)
        return session

    # ------------------------------------------------------------------
    # Insights
    # ------------------------------------------------------------------

    def _build_insights(
        self,
        session: CollaborationSession,
        distribution: dict,
        consensus: Any,
        qc_report: Any,
        conflicts: list,
    ) -> list[str]:
        insights = []

        insights.append(
            f"Mission '{session.mission}' completed with {len(session.agents)} agents: "
            + ", ".join(session.agents) + "."
        )

        insights.append(
            f"Consensus score: {consensus.consensus_score:.1f}/100 "
            f"(threshold: {consensus.threshold}). "
            f"{'Approved.' if consensus.approved else 'Rejected — score below threshold.'}"
        )

        if consensus.score_spread > 20:
            insights.append(
                f"Score divergence of {consensus.score_spread:.1f} points detected. "
                "Reviewers had notable disagreements."
            )

        if qc_report.checks_failed:
            insights.append(
                f"Quality control flagged: {'; '.join(qc_report.checks_failed[:2])}."
            )
        else:
            insights.append("All quality control checks passed.")

        if conflicts:
            resolved = [c for c in conflicts if c.resolved]
            insights.append(
                f"{len(conflicts)} conflict(s) detected, "
                f"{len(resolved)} auto-resolved via "
                f"{resolved[0].resolution if resolved else 'N/A'}."
            )

        return insights

    # ------------------------------------------------------------------
    # Read-only helpers
    # ------------------------------------------------------------------

    def get_status(self) -> dict[str, Any]:
        """Build the full status payload for GET /collaboration/status."""
        metrics  = self._memory.session_metrics()
        breakdown = self._memory.mission_breakdown()
        sessions = self._memory.list_sessions()
        insights = self._memory.generate_insights(sessions)
        consensus_analytics = self._consensus.analytics()
        quality_analytics   = self._qc.analytics()
        missions = list(get_all_agent_missions())

        return {
            "status":    "operational",
            "layer":     "Multi-Agent Collaborative Execution Layer",
            "version":   "1.0.0",
            "protected_dashboard": "yallaplays.com/admin/os",
            "metrics":   {**metrics, "consensus": consensus_analytics, "quality": quality_analytics},
            "missions_available": missions,
            "mission_breakdown":  breakdown,
            "operational_insights": insights,
            "policy": {
                "reviewer_implementer_separation": True,
                "validator_independence":          True,
                "min_reviewers":  1,
                "min_validators": 1,
                "consensus_threshold": 75.0,
                "quality_threshold":   70.0,
                "single_agent_allowed": False,
            },
        }


def get_all_agent_missions() -> list[str]:
    from .agent_roles import list_mission_names
    return list_mission_names()


# Module-level singleton
_engine = CollaborationEngine()


def get_engine() -> CollaborationEngine:
    return _engine
