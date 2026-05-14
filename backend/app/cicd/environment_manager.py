from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "cicd"

DEFAULT_ENVIRONMENTS = {
    "yallaplays": {
        "development": {"url": "http://localhost:3000", "protected": False, "auto_deploy": True},
        "staging": {"url": "https://staging.yallaplays.com", "protected": False, "auto_deploy": True},
        "production": {"url": "https://yallaplays.com", "protected": True, "auto_deploy": False},
    },
    "fionera": {
        "development": {"url": "http://localhost:3001", "protected": False, "auto_deploy": True},
        "staging": {"url": "https://staging.fionera.com", "protected": False, "auto_deploy": True},
        "production": {"url": "https://fionera.com", "protected": True, "auto_deploy": False},
    },
}


class EnvironmentManager:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._env_path = MEMORY_DIR / "environments.json"
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        if not self._env_path.exists():
            self._env_path.write_text(json.dumps(DEFAULT_ENVIRONMENTS, indent=2))

    def _load(self) -> dict:
        try:
            return json.loads(self._env_path.read_text())
        except Exception:
            return DEFAULT_ENVIRONMENTS

    def get_environments(self, project_id: str | None = None) -> dict:
        data = self._load()
        if project_id:
            return {project_id: data.get(project_id, {})}
        return data

    def get_environment(self, project_id: str, environment: str) -> dict | None:
        data = self._load()
        return data.get(project_id, {}).get(environment)

    def is_protected(self, project_id: str, environment: str) -> bool:
        env = self.get_environment(project_id, environment)
        if env is None:
            return True
        return env.get("protected", True)

    def allows_auto_deploy(self, project_id: str, environment: str) -> bool:
        env = self.get_environment(project_id, environment)
        if env is None:
            return False
        if self.is_protected(project_id, environment):
            return False
        return env.get("auto_deploy", False)

    def get_env_url(self, project_id: str, environment: str) -> str | None:
        env = self.get_environment(project_id, environment)
        return env.get("url") if env else None
