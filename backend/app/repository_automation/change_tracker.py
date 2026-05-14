from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import RepositoryChange, ChangeAudit, ChangeStatus, ChangeType


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "repository_automation"


class ChangeTracker:
    def __init__(self):
        self._changes_path = MEMORY_DIR / "changes.json"
        self._audit_path = MEMORY_DIR / "audit.json"
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except Exception:
            return []

    def _save(self, path: Path, data: list[dict]) -> None:
        path.write_text(json.dumps(data, indent=2, default=str))

    def record_change(self, change: RepositoryChange) -> RepositoryChange:
        changes = self._load(self._changes_path)
        changes.append(change.model_dump())
        self._save(self._changes_path, changes)
        self._audit("record_change", change.id, "RepositoryChange", {"status": change.status})
        return change

    def update_change_status(self, change_id: str, status: ChangeStatus, details: dict | None = None) -> bool:
        changes = self._load(self._changes_path)
        updated = False
        for c in changes:
            if c["id"] == change_id:
                c["status"] = status.value if hasattr(status, "value") else status
                c["updated_at"] = datetime.utcnow().isoformat()
                if details:
                    c.setdefault("metadata", {}).update(details)
                updated = True
                break
        if updated:
            self._save(self._changes_path, changes)
            self._audit("update_status", change_id, "RepositoryChange", {"new_status": status})
        return updated

    def get_changes(self, project_id: str | None = None, status: str | None = None) -> list[dict]:
        changes = self._load(self._changes_path)
        if project_id:
            changes = [c for c in changes if c.get("project_id") == project_id]
        if status:
            changes = [c for c in changes if c.get("status") == status]
        return changes

    def get_change(self, change_id: str) -> dict | None:
        for c in self._load(self._changes_path):
            if c["id"] == change_id:
                return c
        return None

    def _audit(self, action: str, entity_id: str, entity_type: str, details: dict, success: bool = True, error: str | None = None) -> None:
        try:
            audits = self._load(self._audit_path)
            entry = ChangeAudit(
                action=action,
                entity_id=entity_id,
                entity_type=entity_type,
                details=details,
                success=success,
                error=error,
            )
            audits.append(entry.model_dump())
            self._save(self._audit_path, audits)
        except Exception:
            pass

    def get_audit_trail(self, entity_id: str | None = None) -> list[dict]:
        audits = self._load(self._audit_path)
        if entity_id:
            audits = [a for a in audits if a.get("entity_id") == entity_id]
        return audits
