from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import Release, ReleaseStatus


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "cicd"


class ReleaseTracking:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._path = MEMORY_DIR / "releases.json"

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._path.write_text(json.dumps(data, indent=2, default=str))

    def create_release(self, project_id: str, version: str, tag: str, changelog: str = "") -> Release:
        release = Release(
            project_id=project_id,
            version=version,
            tag=tag,
            changelog=changelog,
            status=ReleaseStatus.draft,
        )
        data = self._load()
        data.append(release.model_dump())
        self._save(data)
        return release

    def mark_released(self, release_id: str, environment: str) -> bool:
        data = self._load()
        for r in data:
            if r["id"] == release_id:
                if environment not in r["deployed_envs"]:
                    r["deployed_envs"].append(environment)
                if "production" in r["deployed_envs"]:
                    r["status"] = "released"
                    r["released_at"] = datetime.utcnow().isoformat()
                self._save(data)
                return True
        return False

    def list_releases(self, project_id: str | None = None, status: str | None = None) -> list[dict]:
        data = self._load()
        if project_id:
            data = [r for r in data if r.get("project_id") == project_id]
        if status:
            data = [r for r in data if r.get("status") == status]
        return sorted(data, key=lambda x: x.get("created_at", ""), reverse=True)

    def get_latest_by_project(self) -> dict[str, str]:
        data = self._load()
        latest: dict[str, str] = {}
        for r in sorted(data, key=lambda x: x.get("created_at", "")):
            pid = r.get("project_id", "")
            if pid:
                latest[pid] = r.get("version", "unknown")
        return latest

    def get_release(self, release_id: str) -> dict | None:
        for r in self._load():
            if r["id"] == release_id:
                return r
        return None
