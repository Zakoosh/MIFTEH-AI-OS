"""
patch_executor.py — Generates and applies file patches.

Uses difflib to produce unified diffs. Writes are always backed up
by the RollbackManager before any modification occurs.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path
from typing import Any

from .models import Patch, new_operation_id


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

PATCHES_DIR = Path("app/memory/apply/patches")


def _ensure_dirs() -> None:
    PATCHES_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# PatchExecutor
# ---------------------------------------------------------------------------

class PatchExecutor:
    """Generates patches from a change specification and applies them safely."""

    def generate_patch(
        self,
        operation_id: str,
        proposal_id: str,
        target_file: str,
        original_content: str,
        patched_content: str,
    ) -> Patch:
        """Produce a Patch object containing a unified diff."""

        diff_lines = list(
            difflib.unified_diff(
                original_content.splitlines(keepends=True),
                patched_content.splitlines(keepends=True),
                fromfile=f"a/{target_file}",
                tofile=f"b/{target_file}",
                lineterm="",
            )
        )

        patch = Patch(
            operation_id=operation_id,
            proposal_id=proposal_id,
            target_file=target_file,
            original_content=original_content,
            patched_content=patched_content,
            diff_lines=diff_lines,
        )

        self._persist_patch(patch)
        return patch

    def apply_patch(self, patch: Patch, dry_run: bool = False) -> tuple[bool, str]:
        """Write patched_content to the target file.

        Returns (success, message). If dry_run=True, skips the actual write.
        """
        target_path = Path(patch.target_file)

        if dry_run:
            return True, "dry_run: patch not written to disk"

        if not target_path.parent.exists():
            return (
                False,
                f"Parent directory does not exist: {target_path.parent}. "
                "Operation logged as simulated.",
            )

        try:
            target_path.write_text(patch.patched_content, encoding="utf-8")
            return True, f"Patch applied to {target_path}"
        except OSError as exc:
            return False, f"OSError writing {target_path}: {exc}"

    def read_target_content(self, target_file: str) -> tuple[str, bool]:
        """Read the current content of target_file.

        Returns (content, exists). When the file does not exist, returns
        an empty string and exists=False (simulated mode).
        """
        path = Path(target_file)
        if path.exists():
            try:
                return path.read_text(encoding="utf-8"), True
            except OSError:
                return "", False
        return "", False

    def build_patched_content(
        self,
        original_content: str,
        target_file: str,
        changes: dict[str, Any],
        exists: bool,
    ) -> str:
        """Build the new file content by applying structured changes.

        For JSON files: loads JSON, merges changes, serializes back.
        For other files: appends a structured comment block.
        When the file does not exist (simulated), generates synthetic content.
        """
        suffix = Path(target_file).suffix.lower()

        if suffix == ".json":
            return self._patch_json(original_content, changes, exists)
        elif suffix in {".html", ".htm"}:
            return self._patch_html(original_content, changes, exists)
        else:
            return self._patch_text(original_content, changes, exists)

    # ------------------------------------------------------------------
    # Internal patchers
    # ------------------------------------------------------------------

    def _patch_json(
        self, original: str, changes: dict[str, Any], exists: bool
    ) -> str:
        if exists and original.strip():
            try:
                data = json.loads(original)
            except json.JSONDecodeError:
                data = {}
        else:
            data = {}

        data.update(changes)
        return json.dumps(data, indent=2, ensure_ascii=False) + "\n"

    def _patch_html(
        self, original: str, changes: dict[str, Any], exists: bool
    ) -> str:
        if not exists or not original.strip():
            original = "<html><head></head><body></body></html>"

        # Inject meta tags for SEO-style changes
        meta_block = "\n".join(
            f'  <meta name="{k}" content="{v}" />'
            for k, v in changes.items()
            if isinstance(v, str)
        )

        if "<head>" in original and meta_block:
            return original.replace("<head>", f"<head>\n{meta_block}", 1)
        return original + f"\n<!-- MIFTEH-APPLY: {json.dumps(changes)} -->\n"

    def _patch_text(
        self, original: str, changes: dict[str, Any], exists: bool
    ) -> str:
        change_block = "\n".join(f"  {k}: {v}" for k, v in changes.items())
        marker = "# MIFTEH-APPLY-PATCH\n" + change_block + "\n"

        if "# MIFTEH-APPLY-PATCH" in original:
            # Replace existing patch block
            lines = original.split("\n")
            new_lines = [l for l in lines if not l.startswith("  ") or "MIFTEH" not in original]
            return "\n".join(new_lines) + "\n" + marker

        return (original or "") + ("\n" if original and not original.endswith("\n") else "") + marker

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _persist_patch(self, patch: Patch) -> None:
        _ensure_dirs()
        path = PATCHES_DIR / f"{patch.operation_id}.json"
        try:
            path.write_text(
                json.dumps(patch.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass  # Non-fatal: patch data is still in memory

    def load_patch(self, operation_id: str) -> Patch | None:
        """Load a previously persisted patch from disk."""
        _ensure_dirs()
        path = PATCHES_DIR / f"{operation_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return Patch(**{k: v for k, v in data.items() if k in Patch.__dataclass_fields__})
        except Exception:
            return None
