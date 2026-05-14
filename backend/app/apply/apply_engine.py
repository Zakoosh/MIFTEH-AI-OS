"""
apply_engine.py — Core orchestrator for the Safe Autonomous Apply Layer.

Execution flow:
  Proposal → Validation → Preview → Patch → Apply → Audit → Rollback Support

This module wires together all sub-components and enforces the
"no unsafe autonomous overwrite" policy.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import (
    AuditEntry,
    ApplyResult,
    PreviewResult,
    Proposal,
    new_operation_id,
)
from .validation import validate_proposal
from .patch_executor import PatchExecutor
from .rollback_manager import RollbackManager
from .seo_apply import SEOApplier
from .metadata_apply import MetadataApplier
from .dashboard_apply import DashboardApplier


# ---------------------------------------------------------------------------
# Storage paths
# ---------------------------------------------------------------------------

PREVIEWS_DIR = Path("app/memory/apply/previews")
AUDIT_DIR = Path("app/memory/apply/audit")
RESULTS_DIR = Path("app/memory/apply/results")


def _ensure_dirs() -> None:
    for d in (PREVIEWS_DIR, AUDIT_DIR, RESULTS_DIR):
        d.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# ApplyEngine
# ---------------------------------------------------------------------------

class ApplyEngine:
    """
    Orchestrates the full apply pipeline for a single Proposal.

    Safety guarantees:
    - Only low-risk proposals proceed past validation
    - A backup is created before every file write
    - Audit entries are written for every pipeline stage
    - Simulated mode is used when target paths don't exist
    """

    def __init__(self) -> None:
        self._patch_executor = PatchExecutor()
        self._rollback_manager = RollbackManager()
        self._seo = SEOApplier()
        self._metadata = MetadataApplier()
        self._dashboard = DashboardApplier()

    def run(self, proposal: Proposal, dry_run: bool = False) -> ApplyResult:
        """Execute the full pipeline and return an ApplyResult."""
        _ensure_dirs()
        operation_id = new_operation_id()

        # ── 1. Validation ──────────────────────────────────────────────
        validation = validate_proposal(proposal)
        self._write_audit(AuditEntry(
            operation_id=operation_id,
            proposal_id=proposal.id,
            project_id=proposal.project_id,
            action="validate",
            status="success" if validation.valid else "failure",
            details=validation.to_dict(),
        ))

        if not validation.valid:
            result = ApplyResult(
                proposal_id=proposal.id,
                operation_id=operation_id,
                project=proposal.project_id,
                validated=False,
                preview_generated=False,
                patch_generated=False,
                applied=False,
                rollback_available=False,
                message=validation.message,
                details={"validation": validation.to_dict()},
            )
            self._save_result(result)
            return result

        # ── 2. Preview ─────────────────────────────────────────────────
        preview = self._generate_preview(proposal, operation_id)
        self._write_audit(AuditEntry(
            operation_id=operation_id,
            proposal_id=proposal.id,
            project_id=proposal.project_id,
            action="preview",
            status="success",
            details=preview.to_dict(),
        ))

        # ── 3. Read original content ───────────────────────────────────
        original_content, exists = self._patch_executor.read_target_content(
            proposal.target_file
        )
        simulated = not exists

        # ── 4. Build patched content ───────────────────────────────────
        prepared_changes = self._prepare_changes(proposal)
        patched_content = self._patch_executor.build_patched_content(
            original_content, proposal.target_file, prepared_changes, exists
        )

        # ── 5. Generate patch ──────────────────────────────────────────
        patch = self._patch_executor.generate_patch(
            operation_id=operation_id,
            proposal_id=proposal.id,
            target_file=proposal.target_file,
            original_content=original_content,
            patched_content=patched_content,
        )
        self._write_audit(AuditEntry(
            operation_id=operation_id,
            proposal_id=proposal.id,
            project_id=proposal.project_id,
            action="patch",
            status="success",
            details={
                "diff_lines": len(patch.diff_lines),
                "target_file": patch.target_file,
                "simulated": simulated,
            },
        ))

        # ── 6. Save backup (before apply) ─────────────────────────────
        self._rollback_manager.save_backup(
            operation_id=operation_id,
            proposal_id=proposal.id,
            target_file=proposal.target_file,
            original_content=original_content,
        )

        # ── 7. Apply ───────────────────────────────────────────────────
        applied, apply_msg = self._patch_executor.apply_patch(patch, dry_run=dry_run or simulated)
        self._write_audit(AuditEntry(
            operation_id=operation_id,
            proposal_id=proposal.id,
            project_id=proposal.project_id,
            action="apply",
            status="success" if applied else "failure",
            details={
                "message": apply_msg,
                "dry_run": dry_run,
                "simulated": simulated,
            },
        ))

        # ── 8. Build extra details ─────────────────────────────────────
        extra = self._build_extra_details(proposal, prepared_changes)

        result = ApplyResult(
            proposal_id=proposal.id,
            operation_id=operation_id,
            project=proposal.project_id,
            validated=True,
            preview_generated=True,
            patch_generated=True,
            applied=applied or simulated,   # simulated counts as "applied" logically
            rollback_available=True,
            simulated=simulated,
            message=apply_msg if not simulated else "Applied (simulated — target path not accessible)",
            details={
                "validation": validation.to_dict(),
                "preview": preview.to_dict(),
                "patch_diff_lines": len(patch.diff_lines),
                **extra,
            },
        )

        self._save_result(result)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _prepare_changes(self, proposal: Proposal) -> dict[str, Any]:
        """Delegate change preparation to the correct domain applier."""
        if proposal.project_id == "yallaplays":
            if proposal.proposal_type in ("seo", "landing_page", "category", "manifest"):
                return self._seo.prepare_changes(proposal)
        if proposal.proposal_type == "metadata":
            return self._metadata.prepare_changes(proposal)
        if proposal.project_id == "fionera":
            if proposal.proposal_type in ("dashboard", "widget", "watchlist"):
                return self._dashboard.prepare_changes(proposal)
        return dict(proposal.changes)

    def _generate_preview(self, proposal: Proposal, operation_id: str) -> PreviewResult:
        """Generate and persist a PreviewResult."""
        if proposal.project_id == "yallaplays" and proposal.proposal_type in (
            "seo", "landing_page", "category", "manifest"
        ):
            before, after = self._seo.generate_preview_summary(proposal)
        elif proposal.proposal_type == "metadata":
            before, after = self._metadata.generate_preview_summary(proposal)
        elif proposal.project_id == "fionera" and proposal.proposal_type in (
            "dashboard", "widget", "watchlist"
        ):
            before, after = self._dashboard.generate_preview_summary(proposal)
        else:
            before = f"Current state of {proposal.target_file}"
            after = str(proposal.changes)

        _, exists = self._patch_executor.read_target_content(proposal.target_file)

        preview = PreviewResult(
            proposal_id=proposal.id,
            operation_type=proposal.proposal_type,
            target_file=proposal.target_file,
            before_summary=before,
            after_summary=after,
            changes_count=len(proposal.changes),
            simulated=not exists,
        )

        PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        path = PREVIEWS_DIR / f"{proposal.id}_{operation_id}.json"
        try:
            path.write_text(
                json.dumps(preview.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

        return preview

    def _build_extra_details(
        self, proposal: Proposal, prepared_changes: dict[str, Any]
    ) -> dict[str, Any]:
        """Build domain-specific result details."""
        if proposal.project_id == "fionera" and proposal.proposal_type == "widget":
            widget_id = proposal.changes.get("widget_id", "unknown")
            return {
                "project": "fionera",
                "widget_added": widget_id,
                "dashboard_updated": True,
            }
        return {}

    def _write_audit(self, entry: AuditEntry) -> None:
        """Persist an audit entry to disk."""
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        path = AUDIT_DIR / f"{entry.audit_id}.json"
        try:
            path.write_text(
                json.dumps(entry.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    def _save_result(self, result: ApplyResult) -> None:
        """Persist the final ApplyResult."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        path = RESULTS_DIR / f"{result.operation_id}.json"
        try:
            path.write_text(
                json.dumps(result.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Read-only helpers
    # ------------------------------------------------------------------

    def list_history(self) -> list[dict]:
        """Return all apply results, newest first."""
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        items = []
        for file in RESULTS_DIR.glob("*.json"):
            try:
                items.append(json.loads(file.read_text(encoding="utf-8")))
            except Exception:
                pass
        items.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        return items

    def list_previews(self) -> list[dict]:
        """Return all generated previews, newest first."""
        PREVIEWS_DIR.mkdir(parents=True, exist_ok=True)
        items = []
        for file in PREVIEWS_DIR.glob("*.json"):
            try:
                items.append(json.loads(file.read_text(encoding="utf-8")))
            except Exception:
                pass
        items.sort(key=lambda x: x.get("generated_at") or "", reverse=True)
        return items

    def list_audit(self) -> list[dict]:
        """Return all audit entries, newest first."""
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        items = []
        for file in AUDIT_DIR.glob("*.json"):
            try:
                items.append(json.loads(file.read_text(encoding="utf-8")))
            except Exception:
                pass
        items.sort(key=lambda x: x.get("timestamp") or "", reverse=True)
        return items


# Module-level singleton
_engine = ApplyEngine()


def get_engine() -> ApplyEngine:
    return _engine
