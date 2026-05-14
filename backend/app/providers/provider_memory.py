from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "providers"


class ProviderMemory:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._state_path = MEMORY_DIR / "provider_state.json"

    def _load(self) -> dict:
        if not self._state_path.exists():
            return {}
        try:
            return json.loads(self._state_path.read_text())
        except Exception:
            return {}

    def _save(self, data: dict) -> None:
        self._state_path.write_text(json.dumps(data, indent=2, default=str))

    def set(self, key: str, value: object) -> None:
        data = self._load()
        data[key] = value
        data["_updated_at"] = datetime.utcnow().isoformat()
        self._save(data)

    def get(self, key: str, default: object = None) -> object:
        return self._load().get(key, default)

    def get_all(self) -> dict:
        return self._load()

    def record_provider_switch(self, from_provider: str, to_provider: str, reason: str) -> None:
        data = self._load()
        history = data.get("provider_switch_history", [])
        history.append({
            "from": from_provider,
            "to": to_provider,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
        })
        data["provider_switch_history"] = history[-100:]
        data["current_provider"] = to_provider
        self._save(data)

    def get_provider_history(self) -> list[dict]:
        return self._load().get("provider_switch_history", [])
