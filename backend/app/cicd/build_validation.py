from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "cicd"


class BuildValidation:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._log_path = MEMORY_DIR / "build_validations.json"

    def _load(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        try:
            return json.loads(self._log_path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._log_path.write_text(json.dumps(data, indent=2, default=str))

    def validate_build(self, project_id: str, version: str, artifact_path: str | None = None) -> dict:
        checks = []
        checks.append({"name": "version_format", "passed": bool(version and len(version) > 0), "detail": f"Version: {version}"})
        checks.append({"name": "project_known", "passed": project_id in ("yallaplays", "fionera"), "detail": f"Project: {project_id}"})

        if artifact_path:
            path = Path(artifact_path)
            checks.append({"name": "artifact_exists", "passed": path.exists(), "detail": str(artifact_path)})
        else:
            checks.append({"name": "artifact_exists", "passed": True, "detail": "No artifact path provided (skipped)"})

        passed = all(c["passed"] for c in checks)
        result = {
            "project_id": project_id,
            "version": version,
            "passed": passed,
            "checks": checks,
            "validated_at": datetime.utcnow().isoformat(),
        }
        log = self._load()
        log.append(result)
        self._save(log[-100:])
        return result

    def get_validation_history(self, project_id: str | None = None) -> list[dict]:
        data = self._load()
        if project_id:
            data = [v for v in data if v.get("project_id") == project_id]
        return data[-20:]
