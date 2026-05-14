from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import RuntimeOperation, RuntimeCycle


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "runtime"


class RuntimeMemory:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._ops_path = MEMORY_DIR / "operations.json"
        self._cycles_path = MEMORY_DIR / "cycles.json"
        self._state_path = MEMORY_DIR / "state.json"

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except Exception:
            return []

    def _save(self, path: Path, data: list[dict]) -> None:
        path.write_text(json.dumps(data, indent=2, default=str))

    def save_operation(self, op: RuntimeOperation) -> None:
        data = self._load(self._ops_path)
        for i, o in enumerate(data):
            if o["id"] == op.id:
                data[i] = op.model_dump()
                self._save(self._ops_path, data)
                return
        data.append(op.model_dump())
        self._save(self._ops_path, data[-2000:])

    def get_operations(self, project: str | None = None, status: str | None = None, limit: int = 100) -> list[dict]:
        data = self._load(self._ops_path)
        if project:
            data = [o for o in data if o.get("project") == project]
        if status:
            data = [o for o in data if o.get("status") == status]
        return data[-limit:]

    def get_operation(self, op_id: str) -> dict | None:
        for o in self._load(self._ops_path):
            if o["id"] == op_id:
                return o
        return None

    def save_cycle(self, cycle: RuntimeCycle) -> None:
        data = self._load(self._cycles_path)
        for i, c in enumerate(data):
            if c["id"] == cycle.id:
                data[i] = cycle.model_dump()
                self._save(self._cycles_path, data)
                return
        data.append(cycle.model_dump())
        self._save(self._cycles_path, data[-500:])

    def get_cycles(self, project: str | None = None, limit: int = 20) -> list[dict]:
        data = self._load(self._cycles_path)
        if project:
            data = [c for c in data if c.get("project") == project]
        return data[-limit:]

    def get_last_cycle(self) -> dict | None:
        data = self._load(self._cycles_path)
        return data[-1] if data else None

    def get_cycle_count_today(self) -> int:
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        return len([c for c in self._load(self._cycles_path) if c.get("started_at", "") >= cutoff])

    def get_state(self) -> dict:
        if not self._state_path.exists():
            return {"mode": "manual", "started_at": datetime.utcnow().isoformat()}
        try:
            return json.loads(self._state_path.read_text())
        except Exception:
            return {}

    def set_state(self, key: str, value: object) -> None:
        state = self.get_state()
        state[key] = value
        state["_updated_at"] = datetime.utcnow().isoformat()
        self._state_path.write_text(json.dumps(state, indent=2, default=str))
