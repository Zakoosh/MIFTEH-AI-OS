from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import json
from .models import ProviderHealth, ProviderStatus
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "providers"


class ProviderHealthMonitor:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._health_path = MEMORY_DIR / "health.json"
        self._openai = OpenAIProvider()
        self._gemini = GeminiProvider()

    def _load(self) -> list[dict]:
        if not self._health_path.exists():
            return []
        try:
            return json.loads(self._health_path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._health_path.write_text(json.dumps(data, indent=2, default=str))

    async def check_all(self) -> list[dict]:
        results = []
        for provider_cls, name in [(self._openai, "openai"), (self._gemini, "gemini")]:
            try:
                health = await provider_cls.health_check()
                results.append(health)
            except Exception as e:
                results.append({"provider": name, "status": "unavailable", "error": str(e)})
        results.append({"provider": "mock", "status": "healthy", "is_configured": True, "latency_ms": 0.0})
        self._save(results)
        return results

    def get_cached_health(self) -> list[dict]:
        data = self._load()
        if not data:
            return [
                {"provider": "openai", "status": "unknown" if not self._openai.is_configured() else "healthy", "is_configured": self._openai.is_configured()},
                {"provider": "gemini", "status": "unknown" if not self._gemini.is_configured() else "healthy", "is_configured": self._gemini.is_configured()},
                {"provider": "mock", "status": "healthy", "is_configured": True},
            ]
        return data

    def get_overall_status(self) -> str:
        health = self.get_cached_health()
        statuses = [h.get("status", "unknown") for h in health]
        if any(s == "healthy" for s in statuses):
            return "healthy"
        if any(s == "degraded" for s in statuses):
            return "degraded"
        return "unavailable"

    def compute_avg_latency(self) -> float:
        health = self.get_cached_health()
        latencies = [h.get("latency_ms", 0) for h in health if h.get("latency_ms") is not None]
        return round(sum(latencies) / len(latencies), 2) if latencies else 0.0
