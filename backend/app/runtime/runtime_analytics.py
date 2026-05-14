from __future__ import annotations
from datetime import datetime, timedelta
from .models import RuntimeAnalytics
from .runtime_memory import RuntimeMemory


class RuntimeAnalyticsEngine:
    def __init__(self):
        self._memory = RuntimeMemory()

    def compute(self, period: str = "24h") -> RuntimeAnalytics:
        hours = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}.get(period, 24)
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()

        ops = self._memory.get_operations(limit=2000)
        ops = [o for o in ops if o.get("created_at", "") >= cutoff]

        total = len(ops)
        completed = [o for o in ops if o.get("status") == "completed"]
        success_rate = round((len(completed) / total) * 100, 2) if total else 100.0

        durations = []
        for o in completed:
            s, e = o.get("started_at"), o.get("completed_at")
            if s and e:
                try:
                    dur = (datetime.fromisoformat(str(e).replace("Z", "")) - datetime.fromisoformat(str(s).replace("Z", ""))).total_seconds()
                    durations.append(dur)
                except Exception:
                    pass

        avg_duration = round(sum(durations) / len(durations), 2) if durations else 0.0
        total_cost = round(sum(o.get("actual_cost", 0) for o in ops), 6)

        project_counts: dict[str, int] = {}
        for o in ops:
            p = o.get("project", "unknown")
            project_counts[p] = project_counts.get(p, 0) + 1
        top_projects = sorted(project_counts, key=lambda x: project_counts[x], reverse=True)[:5]

        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for o in ops:
            t = o.get("operation_type", "unknown")
            s = o.get("status", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            by_status[s] = by_status.get(s, 0) + 1

        return RuntimeAnalytics(
            period=period,
            total_operations=total,
            success_rate=success_rate,
            avg_duration_seconds=avg_duration,
            total_cost_usd=total_cost,
            top_projects=top_projects,
            operations_by_type=by_type,
            operations_by_status=by_status,
        )

    def get_summary_dict(self, period: str = "24h") -> dict:
        return self.compute(period).model_dump()
