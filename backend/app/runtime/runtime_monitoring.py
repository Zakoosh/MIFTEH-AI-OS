from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import RuntimeMetric
from .runtime_memory import RuntimeMemory


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "runtime"


class RuntimeMonitoring:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._metrics_path = MEMORY_DIR / "metrics.json"
        self._memory = RuntimeMemory()

    def _load(self) -> list[dict]:
        if not self._metrics_path.exists():
            return []
        try:
            return json.loads(self._metrics_path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._metrics_path.write_text(json.dumps(data, indent=2, default=str))

    def record_metric(self, name: str, value: float, unit: str = "", project: str = "all", tags: dict | None = None) -> None:
        metric = RuntimeMetric(metric_name=name, value=value, unit=unit, project=project, tags=tags or {})
        data = self._load()
        data.append(metric.model_dump())
        self._save(data[-5000:])

    def get_metrics(self, name: str | None = None, project: str | None = None, limit: int = 100) -> list[dict]:
        data = self._load()
        if name:
            data = [m for m in data if m.get("metric_name") == name]
        if project:
            data = [m for m in data if m.get("project") == project]
        return data[-limit:]

    def compute_op_stats(self) -> dict:
        ops = self._memory.get_operations(limit=500)
        if not ops:
            return {"total": 0, "success_rate": 100.0, "avg_duration": 0.0, "active": 0}
        total = len(ops)
        completed = [o for o in ops if o.get("status") == "completed"]
        failed = [o for o in ops if o.get("status") == "failed"]
        active = [o for o in ops if o.get("status") in ("running", "queued")]
        durations = []
        for o in completed:
            s = o.get("started_at")
            e = o.get("completed_at")
            if s and e:
                try:
                    dur = (datetime.fromisoformat(str(e).replace("Z", "")) - datetime.fromisoformat(str(s).replace("Z", ""))).total_seconds()
                    durations.append(dur)
                except Exception:
                    pass
        return {
            "total": total,
            "completed": len(completed),
            "failed": len(failed),
            "active": len(active),
            "success_rate": round((len(completed) / total) * 100, 2) if total else 100.0,
            "avg_duration": round(sum(durations) / len(durations), 2) if durations else 0.0,
        }

    def check_layer_health(self) -> dict[str, bool]:
        layers = {}
        try:
            from ..delivery.delivery_health import DeliveryHealth
            layers["delivery"] = True
        except Exception:
            layers["delivery"] = False
        try:
            from ..repository_automation.repository_engine import RepositoryEngine
            layers["repository_automation"] = True
        except Exception:
            layers["repository_automation"] = False
        try:
            from ..cicd.deployment_engine import DeploymentEngine
            layers["cicd"] = True
        except Exception:
            layers["cicd"] = False
        try:
            from ..providers.request_manager import RequestManager
            layers["providers"] = True
        except Exception:
            layers["providers"] = False
        return layers
