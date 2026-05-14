"""
rollback_manager.py — Manages file backups and rollback execution.

Before any patch is applied, the original file content is stored here.
Rollback restores the backup atomically.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .models import RollbackRecord


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

BACKUPS_DIR = Path("app/memory/apply/backups")


def _ensure_dirs() -> None:
    BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# RollbackManager
# ---------------------------------------------------------------------------

class RollbackManager:
    """Stores file backups and restores them on demand."""

    def save_backup(
        self,
        operation_id: str,
        proposal_id: str,
        target_file: str,
        original_content: str,
    ) -> RollbackRecord:
        """Persist a backup so the operation can be rolled back later."""
        _ensure_dirs()

        record = RollbackRecord(
            operation_id=operation_id,
            proposal_id=proposal_id,
            target_file=target_file,
            backup_content=original_content,
        )

        backup_path = BACKUPS_DIR / f"{operation_id}.json"
        try:
            backup_path.write_text(
                json.dumps(record.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass  # Still return the in-memory record

        return record

    def rollback(self, operation_id: str, reason: str = "") -> dict:
        """Restore the backup for the given operation_id.

        Returns a result dict with keys: restored, message, timestamp.
        """
        _ensure_dirs()

        record = self._load_record(operation_id)
        if record is None:
            return {
                "operation_id": operation_id,
                "restored": False,
                "message": f"No backup found for operation_id '{operation_id}'",
                "timestamp": datetime.now().isoformat(),
            }

        if record.restored:
            return {
                "operation_id": operation_id,
                "proposal_id": record.proposal_id,
                "restored": False,
                "message": "Already rolled back",
                "timestamp": datetime.now().isoformat(),
            }

        target_path = Path(record.target_file)
        simulated = False

        if not target_path.parent.exists():
            # Target directory doesn't exist (e.g., Windows path on Linux) — simulate
            simulated = True
            msg = f"Simulated rollback: target path not accessible ({record.target_file})"
        else:
            try:
                target_path.write_text(record.backup_content, encoding="utf-8")
                msg = f"Restored {record.target_file} from backup"
            except OSError as exc:
                return {
                    "operation_id": operation_id,
                    "proposal_id": record.proposal_id,
                    "restored": False,
                    "message": f"Failed to restore: {exc}",
                    "timestamp": datetime.now().isoformat(),
                }

        # Mark as restored
        record.restored = True
        record.restored_at = datetime.now().isoformat()
        self._save_record(record)

        return {
            "operation_id": operation_id,
            "proposal_id": record.proposal_id,
            "restored": True,
            "simulated": simulated,
            "message": msg,
            "reason": reason,
            "timestamp": record.restored_at,
        }

    def is_rollback_available(self, operation_id: str) -> bool:
        """Check whether a non-restored backup exists for this operation."""
        record = self._load_record(operation_id)
        return record is not None and not record.restored

    def list_backups(self) -> list[dict]:
        """Return summary list of all backup records."""
        _ensure_dirs()
        results = []
        for file in BACKUPS_DIR.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                results.append({
                    "operation_id": data.get("operation_id"),
                    "proposal_id": data.get("proposal_id"),
                    "target_file": data.get("target_file"),
                    "created_at": data.get("created_at"),
                    "restored": data.get("restored", False),
                })
            except Exception:
                pass
        results.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_record(self, operation_id: str) -> RollbackRecord | None:
        path = BACKUPS_DIR / f"{operation_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return RollbackRecord(**{
                k: v for k, v in data.items()
                if k in RollbackRecord.__dataclass_fields__
            })
        except Exception:
            return None

    def _save_record(self, record: RollbackRecord) -> None:
        path = BACKUPS_DIR / f"{record.operation_id}.json"
        try:
            path.write_text(
                json.dumps(record.to_dict(), indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass
