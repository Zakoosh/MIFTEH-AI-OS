from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import json
from .models import StagingDeployment, DeploymentStatus


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "cicd"


class StagingManager:
    TTL_HOURS = 48

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._path = MEMORY_DIR / "staging.json"

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._path.write_text(json.dumps(data, indent=2, default=str))

    def create_staging(self, project_id: str, branch: str, version: str, preview_url: str | None = None) -> StagingDeployment:
        staging = StagingDeployment(
            project_id=project_id,
            branch=branch,
            version=version,
            preview_url=preview_url or f"https://staging-{branch[:20].replace('/', '-')}.preview.mifteh.com",
            status=DeploymentStatus.staging,
            expires_at=datetime.utcnow() + timedelta(hours=self.TTL_HOURS),
        )
        data = self._load()
        data.append(staging.model_dump())
        self._save(data)
        return staging

    def list_staging(self, project_id: str | None = None, active_only: bool = True) -> list[dict]:
        data = self._load()
        if project_id:
            data = [s for s in data if s.get("project_id") == project_id]
        if active_only:
            data = [s for s in data if s.get("status") == "staging"]
        return data

    def destroy_staging(self, staging_id: str) -> bool:
        data = self._load()
        for s in data:
            if s["id"] == staging_id:
                s["status"] = "cancelled"
                s["destroyed_at"] = datetime.utcnow().isoformat()
                self._save(data)
                return True
        return False

    def expire_old_staging(self) -> int:
        data = self._load()
        now = datetime.utcnow()
        count = 0
        for s in data:
            if s.get("status") != "staging":
                continue
            expires = s.get("expires_at")
            if expires:
                try:
                    exp_dt = datetime.fromisoformat(str(expires).replace("Z", ""))
                    if now > exp_dt:
                        s["status"] = "cancelled"
                        count += 1
                except Exception:
                    pass
        if count:
            self._save(data)
        return count
