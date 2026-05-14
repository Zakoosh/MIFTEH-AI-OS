from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import DeploymentHealth


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "cicd"


class DeploymentMonitor:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._health_path = MEMORY_DIR / "deployment_health.json"

    def _load(self) -> list[dict]:
        if not self._health_path.exists():
            return []
        try:
            return json.loads(self._health_path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._health_path.write_text(json.dumps(data, indent=2, default=str))

    def record_health(self, project_id: str, environment: str, status: str, uptime_pct: float = 100.0, error_rate: float = 0.0) -> DeploymentHealth:
        health = DeploymentHealth(
            project_id=project_id,
            environment=environment,
            status=status,
            uptime_pct=uptime_pct,
            error_rate=error_rate,
        )
        data = self._load()
        updated = False
        for i, h in enumerate(data):
            if h.get("project_id") == project_id and h.get("environment") == environment:
                data[i] = health.model_dump()
                updated = True
                break
        if not updated:
            data.append(health.model_dump())
        self._save(data)
        return health

    def get_all_health(self) -> list[dict]:
        data = self._load()
        if not data:
            return [
                DeploymentHealth(project_id="yallaplays", environment="staging", status="healthy", uptime_pct=99.9).model_dump(),
                DeploymentHealth(project_id="yallaplays", environment="production", status="healthy", uptime_pct=99.95).model_dump(),
                DeploymentHealth(project_id="fionera", environment="staging", status="healthy", uptime_pct=100.0).model_dump(),
                DeploymentHealth(project_id="fionera", environment="production", status="healthy", uptime_pct=99.8).model_dump(),
            ]
        return data

    def get_project_health(self, project_id: str) -> list[dict]:
        return [h for h in self.get_all_health() if h.get("project_id") == project_id]

    def compute_success_rate(self, deployments: list[dict]) -> float:
        if not deployments:
            return 100.0
        succeeded = len([d for d in deployments if d.get("status") == "deployed"])
        return round((succeeded / len(deployments)) * 100, 2)

    def compute_avg_duration(self, deployments: list[dict]) -> float:
        durations = []
        for d in deployments:
            start = d.get("started_at")
            end = d.get("completed_at")
            if start and end:
                try:
                    s = datetime.fromisoformat(str(start).replace("Z", ""))
                    e = datetime.fromisoformat(str(end).replace("Z", ""))
                    durations.append((e - s).total_seconds())
                except Exception:
                    pass
        return round(sum(durations) / len(durations), 2) if durations else 0.0
