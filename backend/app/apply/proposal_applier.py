"""
proposal_applier.py — High-level entry point for applying a proposal by ID.

Loads proposals from:
  1. The file-based proposal store (app/memory/apply/proposals/)
  2. Built-in seeded proposals from seo_apply, metadata_apply, dashboard_apply

Delegates actual execution to ApplyEngine.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import ApplyResult, Proposal
from .apply_engine import get_engine
from .rollback_manager import RollbackManager

# Built-in proposal sources (imported lazily to avoid circular deps)
import app.apply.seo_apply as _seo_module
import app.apply.metadata_apply as _meta_module
import app.apply.dashboard_apply as _dash_module


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

PROPOSALS_DIR = Path("app/memory/apply/proposals")


def _ensure_dirs() -> None:
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Proposal registry
# ---------------------------------------------------------------------------

def _load_builtin_proposals() -> dict[str, dict]:
    """Merge all built-in proposals into a single id → proposal dict."""
    all_proposals: dict[str, dict] = {}
    for module in (_seo_module, _meta_module, _dash_module):
        for p in module.get_builtin_proposals():
            all_proposals[p["id"]] = p
    return all_proposals


def _load_stored_proposals() -> dict[str, dict]:
    """Load user/runtime-created proposals from the file store."""
    _ensure_dirs()
    stored: dict[str, dict] = {}
    for file in PROPOSALS_DIR.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            if "id" in data:
                stored[data["id"]] = data
        except Exception:
            pass
    return stored


def get_all_proposals() -> dict[str, dict]:
    """Return merged proposal registry (stored takes priority over built-in)."""
    registry = _load_builtin_proposals()
    registry.update(_load_stored_proposals())
    return registry


def get_proposal(proposal_id: str) -> Proposal | None:
    """Retrieve a proposal by ID from the registry."""
    registry = get_all_proposals()
    raw = registry.get(proposal_id)
    if raw is None:
        return None
    try:
        return Proposal.from_dict(raw)
    except Exception:
        return None


def save_proposal(proposal: Proposal) -> None:
    """Persist a new or updated proposal to the file store."""
    _ensure_dirs()
    path = PROPOSALS_DIR / f"{proposal.id}.json"
    path.write_text(
        json.dumps(proposal.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def list_proposals() -> list[dict]:
    """Return all proposals as a list, sorted by created_at desc."""
    registry = get_all_proposals()
    items = list(registry.values())
    items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return items


# ---------------------------------------------------------------------------
# ProposalApplier
# ---------------------------------------------------------------------------

class ProposalApplier:
    """Resolves a proposal by ID and runs the full apply pipeline."""

    def __init__(self) -> None:
        self._engine = get_engine()
        self._rollback = RollbackManager()

    def apply(self, proposal_id: str, dry_run: bool = False) -> ApplyResult:
        """Look up proposal_id and run the apply pipeline.

        Returns an ApplyResult. If the proposal is not found, returns a
        rejected ApplyResult without touching any files.
        """
        proposal = get_proposal(proposal_id)

        if proposal is None:
            from .models import new_operation_id
            return ApplyResult(
                proposal_id=proposal_id,
                operation_id=new_operation_id(),
                project="unknown",
                validated=False,
                preview_generated=False,
                patch_generated=False,
                applied=False,
                rollback_available=False,
                message=f"Proposal '{proposal_id}' not found in registry",
            )

        return self._engine.run(proposal, dry_run=dry_run)

    def rollback(self, operation_id: str, reason: str = "") -> dict:
        """Delegate rollback to RollbackManager."""
        return self._rollback.rollback(operation_id, reason=reason)

    def history(self) -> list[dict]:
        return self._engine.list_history()

    def previews(self) -> list[dict]:
        return self._engine.list_previews()

    def audit(self) -> list[dict]:
        return self._engine.list_audit()


# Module-level singleton
_applier = ProposalApplier()


def get_applier() -> ProposalApplier:
    return _applier
