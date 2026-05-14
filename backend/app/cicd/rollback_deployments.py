from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import RollbackRecord


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "cicd"


class RollbackDeployments:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._path = MEMORY_DIR / "rollbacks.json"

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._path.write_text(json.dumps(data, indent=2, default=str))

    def initiate_rollback(self, deployment_id: str, reason: str, target_version: str, initiated_by: str = "system") -> RollbackRecord:
        record = RollbackRecord(
            deployment_id=deployment_id,
            reason=reason,
            target_version=target_version,
            status="initiated",
            initiated_by=initiated_by,
        )
        data = self._load()
        data.append(record.model_dump())
        self._save(data)
        return record

    def complete_rollback(self, rollback_id: str, success: bool, error: str | None = None) -> bool:
        data = self._load()
        for r in data:
            if r["id"] == rollback_id:
                r["status"] = "completed" if success else "failed"
                r["success"] = success
                r["completed_at"] = datetime.utcnow().isoformat()
                r["error"] = error
                self._save(data)
                return True
        return False

    def list_rollbacks(self, deployment_id: str | None = None) -> list[dict]:
        data = self._load()
        if deployment_id:
            data = [r for r in data if r.get("deployment_id") == deployment_id]
        return sorted(data, key=lambda x: x.get("initiated_at", ""), reverse=True)

    def get_rollback(self, rollback_id: str) -> dict | None:
        for r in self._load():
            if r["id"] == rollback_id:
                return r
        return None
