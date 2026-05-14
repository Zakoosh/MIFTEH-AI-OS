from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import json

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .loop_definitions import YALLAPLAYS_LOOPS, FIONERA_LOOPS, MIFTEH_LOOPS, ALL_LOOPS, LOOP_INDEX
from .provider_manager import ProviderCooldownManager


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "scheduler"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

_LOOP_STATE_PATH = MEMORY_DIR / "loop_state.json"


def _load_state() -> dict:
    if not _LOOP_STATE_PATH.exists():
        return {}
    try:
        return json.loads(_LOOP_STATE_PATH.read_text())
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    _LOOP_STATE_PATH.write_text(json.dumps(state, indent=2, default=str))


def _now() -> str:
    return datetime.utcnow().isoformat()


class LoopScheduler:
    """APScheduler-backed continuous operations scheduler.

    Each loop runs at its configured interval, executes the corresponding
    operation via OperationEngine, records results, and updates loop state.
    """

    def __init__(self):
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._cooldowns = ProviderCooldownManager()
        self._state: dict = _load_state()
        self._running = False

        # Lazy import to avoid circular imports at module load time
        self._engine = None

    def _get_engine(self):
        if self._engine is None:
            from ..operations.operation_engine import OperationEngine
            self._engine = OperationEngine()
        return self._engine

    def _init_loop_state(self, loop_id: str) -> None:
        if loop_id not in self._state:
            defn = LOOP_INDEX.get(loop_id, {})
            self._state[loop_id] = {
                "id": loop_id,
                "label": defn.get("label", loop_id),
                "project": defn.get("project", ""),
                "interval_minutes": defn.get("interval_minutes", 60),
                "enabled": True,
                "last_run": None,
                "next_run": None,
                "run_count": 0,
                "success_count": 0,
                "error_count": 0,
                "last_output_id": None,
                "last_status": "pending",
                "last_error": None,
            }

    async def _execute_loop(self, loop_id: str) -> None:
        defn = LOOP_INDEX.get(loop_id)
        if not defn:
            return

        self._init_loop_state(loop_id)
        state = self._state[loop_id]

        if not state.get("enabled", True):
            return

        use_ai = self._cooldowns.should_use_ai()
        state["last_run"] = _now()
        state["run_count"] = state.get("run_count", 0) + 1
        interval = defn.get("interval_minutes", 60)
        state["next_run"] = (datetime.utcnow() + timedelta(minutes=interval)).isoformat()
        state["last_status"] = "running"
        _save_state(self._state)

        try:
            engine = self._get_engine()
            result = await engine.generate(
                project=defn["project"],
                output_type=defn["operation_type"],
                topic=defn.get("topic", ""),
                use_ai=use_ai,
                count=1,
            )

            if result.get("success"):
                state["last_status"] = "completed"
                state["success_count"] = state.get("success_count", 0) + 1
                outputs = result.get("outputs", [])
                if outputs:
                    state["last_output_id"] = outputs[0].get("id")
                    ai_gen = outputs[0].get("ai_generated", False)
                    provider = outputs[0].get("provider", "template")
                    if ai_gen and provider in ("openai", "gemini"):
                        self._cooldowns.record_success(provider)
            else:
                state["last_status"] = "failed"
                state["error_count"] = state.get("error_count", 0) + 1
                state["last_error"] = result.get("error", "unknown")

        except Exception as e:
            state["last_status"] = "error"
            state["error_count"] = state.get("error_count", 0) + 1
            state["last_error"] = str(e)

        _save_state(self._state)

    async def start(self) -> None:
        if self._running:
            return

        for defn in ALL_LOOPS:
            loop_id = defn["id"]
            self._init_loop_state(loop_id)
            interval_minutes = defn["interval_minutes"]
            self._scheduler.add_job(
                self._execute_loop,
                trigger=IntervalTrigger(minutes=interval_minutes),
                id=loop_id,
                name=defn["label"],
                args=[loop_id],
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=300,
            )

        _save_state(self._state)
        self._scheduler.start()
        self._running = True

    async def stop(self) -> None:
        if self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False

    async def trigger_loop(self, loop_id: str) -> dict:
        """Manually trigger a loop immediately (outside its schedule)."""
        if loop_id not in LOOP_INDEX:
            return {"success": False, "error": f"Unknown loop: {loop_id}"}
        await self._execute_loop(loop_id)
        state = self._state.get(loop_id, {})
        return {"success": state.get("last_status") == "completed", "loop_id": loop_id, "status": state.get("last_status")}

    def get_loop_states(self) -> list[dict]:
        result = []
        for defn in ALL_LOOPS:
            lid = defn["id"]
            self._init_loop_state(lid)
            state = dict(self._state[lid])
            try:
                job = self._scheduler.get_job(lid)
                if job and job.next_run_time:
                    state["next_run_scheduled"] = job.next_run_time.isoformat()
            except Exception:
                pass
            result.append(state)
        return result

    def set_loop_enabled(self, loop_id: str, enabled: bool) -> bool:
        if loop_id not in LOOP_INDEX:
            return False
        self._init_loop_state(loop_id)
        self._state[loop_id]["enabled"] = enabled
        _save_state(self._state)
        if enabled:
            self._scheduler.resume_job(loop_id)
        else:
            self._scheduler.pause_job(loop_id)
        return True

    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> dict:
        loops = self.get_loop_states()
        active = sum(1 for l in loops if l.get("enabled") and l.get("last_status") != "error")
        total_runs = sum(l.get("run_count", 0) for l in loops)
        total_success = sum(l.get("success_count", 0) for l in loops)
        return {
            "scheduler_running": self._running,
            "total_loops": len(ALL_LOOPS),
            "active_loops": active,
            "total_runs": total_runs,
            "total_success": total_success,
            "provider_cooldowns": self._cooldowns.get_status(),
            "loops": loops,
        }


# Module-level singleton used by the FastAPI lifespan
_scheduler_instance: LoopScheduler | None = None


def get_scheduler() -> LoopScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = LoopScheduler()
    return _scheduler_instance
