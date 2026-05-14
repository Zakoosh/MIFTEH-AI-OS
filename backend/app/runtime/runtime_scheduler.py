from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import json
from .models import RuntimeSchedule, ScheduleType, OperationType


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "runtime"


class RuntimeScheduler:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._path = MEMORY_DIR / "schedules.json"

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._path.write_text(json.dumps(data, indent=2, default=str))

    def create_schedule(
        self,
        project: str,
        operation_type: OperationType,
        interval_minutes: int | None = None,
        cron_expression: str | None = None,
        max_runs: int | None = None,
    ) -> RuntimeSchedule:
        schedule_type = ScheduleType.interval if interval_minutes else ScheduleType.cron if cron_expression else ScheduleType.once
        next_run = datetime.utcnow() + timedelta(minutes=interval_minutes or 60)
        schedule = RuntimeSchedule(
            project=project,
            schedule_type=schedule_type,
            cron_expression=cron_expression,
            interval_minutes=interval_minutes,
            operation_type=operation_type,
            next_run=next_run,
            max_runs=max_runs,
        )
        data = self._load()
        data.append(schedule.model_dump())
        self._save(data)
        return schedule

    def get_due_schedules(self) -> list[dict]:
        now = datetime.utcnow().isoformat()
        data = self._load()
        due = []
        for s in data:
            if not s.get("enabled"):
                continue
            max_runs = s.get("max_runs")
            run_count = s.get("run_count", 0)
            if max_runs and run_count >= max_runs:
                continue
            next_run = s.get("next_run")
            if next_run and next_run <= now:
                due.append(s)
        return due

    def mark_executed(self, schedule_id: str) -> None:
        data = self._load()
        for s in data:
            if s["id"] == schedule_id:
                s["last_run"] = datetime.utcnow().isoformat()
                s["run_count"] = s.get("run_count", 0) + 1
                interval = s.get("interval_minutes")
                if interval:
                    s["next_run"] = (datetime.utcnow() + timedelta(minutes=interval)).isoformat()
                max_runs = s.get("max_runs")
                if max_runs and s["run_count"] >= max_runs:
                    s["enabled"] = False
                break
        self._save(data)

    def list_schedules(self, project: str | None = None, enabled_only: bool = False) -> list[dict]:
        data = self._load()
        if project:
            data = [s for s in data if s.get("project") == project]
        if enabled_only:
            data = [s for s in data if s.get("enabled")]
        return data

    def disable_schedule(self, schedule_id: str) -> bool:
        data = self._load()
        for s in data:
            if s["id"] == schedule_id:
                s["enabled"] = False
                self._save(data)
                return True
        return False
