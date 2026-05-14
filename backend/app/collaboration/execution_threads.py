"""
execution_threads.py — Multi-agent execution thread management.

Each collaboration session spawns one ExecutionThread per task/proposal.
Threads track the full lifecycle from assignment → contribution → review → consensus.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import (
    AgentContribution,
    ExecutionThread,
    THREAD_PENDING,
    THREAD_RUNNING,
    THREAD_REVIEW,
    THREAD_APPROVED,
    THREAD_REJECTED,
    THREAD_COMPLETED,
    now_iso,
)


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

THREADS_DIR       = Path("app/memory/collaboration/threads")
CONTRIBUTIONS_DIR = Path("app/memory/collaboration/contributions")


def _ensure_dirs() -> None:
    THREADS_DIR.mkdir(parents=True, exist_ok=True)
    CONTRIBUTIONS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# ExecutionThreadManager
# ---------------------------------------------------------------------------

class ExecutionThreadManager:
    """Creates, advances, and persists execution threads."""

    # ------------------------------------------------------------------
    # Thread lifecycle
    # ------------------------------------------------------------------

    def create(
        self,
        session_id: str,
        mission: str,
        proposal_id: str,
        project_id: str,
        agent_roles: dict[str, str],
    ) -> ExecutionThread:
        """Instantiate and persist a new thread in PENDING state."""
        _ensure_dirs()

        implementers = [a for a, r in agent_roles.items() if r == "implementer"]
        reviewers    = [a for a, r in agent_roles.items() if r == "reviewer"]
        validators   = [a for a, r in agent_roles.items() if r in ("validator", "qa")]

        thread = ExecutionThread(
            session_id=session_id,
            mission=mission,
            proposal_id=proposal_id,
            project_id=project_id,
            agents=list(agent_roles.keys()),
            agent_roles=agent_roles,
            implementers=implementers,
            reviewers=reviewers,
            validators=validators,
            status=THREAD_PENDING,
        )
        self._save_thread(thread)
        return thread

    def advance(self, thread: ExecutionThread, new_status: str) -> ExecutionThread:
        """Transition thread to a new status and persist."""
        thread.status = new_status
        self._save_thread(thread)
        return thread

    def complete(
        self,
        thread: ExecutionThread,
        approved: bool,
        consensus_score: float,
        quality_score: float,
        error: str = "",
    ) -> ExecutionThread:
        thread.complete(approved=approved, error=error)
        thread.consensus_score = round(consensus_score, 1)
        thread.quality_score   = round(quality_score, 1)
        thread.status = THREAD_APPROVED if approved else THREAD_REJECTED
        thread.completed_at = now_iso()
        self._save_thread(thread)
        return thread

    # ------------------------------------------------------------------
    # Agent execution (offline simulation)
    # ------------------------------------------------------------------

    def execute_agent(
        self,
        thread: ExecutionThread,
        agent_name: str,
        role: str,
        task: str,
        session_id: str,
    ) -> AgentContribution:
        """
        Run one agent's contribution.

        Uses an offline simulation model (no OpenAI call) that produces
        deterministic, realistic outputs based on agent name + task.
        Falls back gracefully when the actual agent runner fails.
        """
        _ensure_dirs()

        output, score, confidence = self._simulate_contribution(agent_name, role, task, thread.mission)

        contribution = AgentContribution(
            thread_id=thread.thread_id,
            session_id=session_id,
            agent_name=agent_name,
            role=role,
            task=task,
            output=output,
            score=score,
            confidence=confidence,
            simulated=True,
        )

        self._save_contribution(contribution)
        thread.contribution_ids.append(contribution.contribution_id)
        self._save_thread(thread)
        return contribution

    # ------------------------------------------------------------------
    # Retrieval
    # ------------------------------------------------------------------

    def get_thread(self, thread_id: str) -> ExecutionThread | None:
        _ensure_dirs()
        path = THREADS_DIR / f"{thread_id}.json"
        if not path.exists():
            return None
        try:
            return ExecutionThread.from_dict(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except Exception:
            return None

    def list_all(self) -> list[ExecutionThread]:
        _ensure_dirs()
        threads = []
        for f in THREADS_DIR.glob("*.json"):
            try:
                threads.append(ExecutionThread.from_dict(
                    json.loads(f.read_text(encoding="utf-8"))
                ))
            except Exception:
                pass
        threads.sort(key=lambda t: t.started_at, reverse=True)
        return threads

    def get_contribution(self, cid: str) -> AgentContribution | None:
        _ensure_dirs()
        path = CONTRIBUTIONS_DIR / f"{cid}.json"
        if not path.exists():
            return None
        try:
            return AgentContribution.from_dict(
                json.loads(path.read_text(encoding="utf-8"))
            )
        except Exception:
            return None

    def get_contributions_for_thread(self, thread: ExecutionThread) -> list[AgentContribution]:
        return [
            c for cid in thread.contribution_ids
            if (c := self.get_contribution(cid)) is not None
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _simulate_contribution(
        self,
        agent_name: str,
        role: str,
        task: str,
        mission: str,
    ) -> tuple[str, float, float]:
        """
        Deterministic offline simulation of an agent contribution.
        Returns (output_text, self_score, confidence).
        """
        import hashlib
        h = int(hashlib.sha256(f"{agent_name}:{mission}:{role}".encode()).hexdigest(), 16)
        variance = (h % 20) - 4   # -4 to +15

        if role == "implementer":
            base_score = 80.0
            output = (
                f"[{agent_name.upper()}] Implementation report for '{mission}':\n"
                f"Task: {task}\n"
                f"Completed: Applied changes according to mission specifications. "
                f"Verified compatibility with existing codebase. "
                f"No breaking changes introduced. Code follows project conventions."
            )
        elif role == "reviewer":
            base_score = 82.0
            output = (
                f"[{agent_name.upper()}] Review report for '{mission}':\n"
                f"Task: {task}\n"
                f"Review outcome: Implementation reviewed. Logic is sound and aligned "
                f"with project goals. Code quality meets standards. Approved with minor suggestions."
            )
        else:   # validator / qa
            base_score = 85.0
            output = (
                f"[{agent_name.upper()}] Validation report for '{mission}':\n"
                f"Task: {task}\n"
                f"Validation outcome: Independent validation passed. Performance benchmarks "
                f"within acceptable range. No critical issues detected. Safe to proceed."
            )

        score      = round(min(100.0, max(60.0, base_score + variance)), 1)
        confidence = round(min(100.0, max(55.0, base_score + (variance * 0.7))), 1)
        return output, score, confidence

    def _save_thread(self, thread: ExecutionThread) -> None:
        _ensure_dirs()
        path = THREADS_DIR / f"{thread.thread_id}.json"
        try:
            path.write_text(
                json.dumps(thread.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _save_contribution(self, c: AgentContribution) -> None:
        _ensure_dirs()
        path = CONTRIBUTIONS_DIR / f"{c.contribution_id}.json"
        try:
            path.write_text(
                json.dumps(c.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass


# Module-level singleton
_manager = ExecutionThreadManager()


def get_thread_manager() -> ExecutionThreadManager:
    return _manager
