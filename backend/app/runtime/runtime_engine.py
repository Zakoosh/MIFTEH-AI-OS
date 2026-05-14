from __future__ import annotations
from datetime import datetime
from pathlib import Path
from .models import RuntimeOperation, RuntimeCycle, OperationType, OperationStatus, RuntimeMode
from .runtime_memory import RuntimeMemory
from .runtime_limits import RuntimeLimits
from .continuous_operations import ContinuousOperations
from .runtime_monitoring import RuntimeMonitoring
from .runtime_analytics import RuntimeAnalyticsEngine
from .runtime_feedback import RuntimeFeedbackSystem
from .runtime_scheduler import RuntimeScheduler


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "runtime"
KNOWN_PROJECTS = ["yallaplays", "fionera"]


class RuntimeEngine:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._memory = RuntimeMemory()
        self._limits = RuntimeLimits()
        self._ops = ContinuousOperations()
        self._monitor = RuntimeMonitoring()
        self._analytics = RuntimeAnalyticsEngine()
        self._feedback = RuntimeFeedbackSystem()
        self._scheduler = RuntimeScheduler()
        self._started_at = datetime.utcnow()

    def run(self, project: str, mode: RuntimeMode = RuntimeMode.manual, operation_type: OperationType = OperationType.health_check, trust_score: float = 0.5) -> dict:
        if project not in KNOWN_PROJECTS and project != "all":
            return {"success": False, "error": f"Unknown project: {project}. Known: {KNOWN_PROJECTS}", "blocked_by": "project_validation"}

        can_run, reason = self._limits.can_execute(trust_score)
        if not can_run:
            return {"success": False, "error": reason, "blocked_by": "safety_limits"}

        if mode in (RuntimeMode.continuous, "continuous") and trust_score < 0.6:
            return {"success": False, "error": "Continuous mode requires trust_score >= 0.6", "blocked_by": "trust_gate"}

        projects = KNOWN_PROJECTS if project == "all" else [project]
        cycles = []
        for proj in projects:
            cycle = self._ops.run_cycle(
                project=proj,
                operation_types=[operation_type.value if hasattr(operation_type, "value") else operation_type],
                trust_score=trust_score,
                mode=mode,
            )
            cycles.append(cycle)
            self._monitor.record_metric("cycle_completed", 1, "count", proj)

        main_cycle = cycles[0] if cycles else None
        return {
            "success": True,
            "operation_id": str(main_cycle.id) if main_cycle else None,
            "cycle_id": str(main_cycle.id) if main_cycle else None,
            "message": f"Runtime cycle completed for {project}",
        }

    def get_status(self) -> dict:
        ops = self._memory.get_operations(limit=200)
        active_ops = [o for o in ops if o.get("status") in ("running", "queued")]
        limits = self._limits.get_limits_status()
        mode = self._memory.get_state().get("mode", "manual")
        return {
            "status": "operational",
            "mode": mode,
            "active_operations": len(active_ops),
            "queued_operations": len([o for o in active_ops if o.get("status") == "queued"]),
            "cycles_today": self._memory.get_cycle_count_today(),
            "limits": limits,
            "safety_active": True,
            "bounded_autonomy": True,
        }

    def get_operations(self, project: str | None = None, status: str | None = None, limit: int = 50) -> list[dict]:
        return self._memory.get_operations(project=project, status=status, limit=limit)

    def get_analytics(self, period: str = "24h") -> dict:
        return self._analytics.get_summary_dict(period)

    def get_health(self) -> dict:
        layers = self._monitor.check_layer_health()
        limits = self._limits.get_limits_status()
        last_cycle = self._memory.get_last_cycle()
        uptime = (datetime.utcnow() - self._started_at).total_seconds() / 3600
        overall = "healthy" if all(layers.values()) else "degraded"
        return {
            "status": overall,
            "layers_healthy": layers,
            "limits_status": limits,
            "last_cycle": last_cycle,
            "uptime_hours": round(uptime, 2),
            "checked_at": datetime.utcnow().isoformat(),
        }
