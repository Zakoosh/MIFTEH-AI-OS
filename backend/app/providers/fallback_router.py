from __future__ import annotations
import asyncio
from datetime import datetime
from pathlib import Path
import json
from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .models import FallbackEvent


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "providers"


class MockProvider:
    PROVIDER_TYPE = "mock"
    DEFAULT_MODEL = "mock-v1"

    def is_configured(self) -> bool:
        return True

    def get_cost_estimate(self, input_tokens: int, output_tokens: int = 0) -> float:
        return 0.0

    async def complete(self, prompt: str, max_tokens: int = 1000, **kwargs) -> dict:
        await asyncio.sleep(0.05)
        return {
            "success": True,
            "response": f"[Mock response to: {prompt[:80]}...]",
            "provider": self.PROVIDER_TYPE,
            "model": self.DEFAULT_MODEL,
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": 20,
            "total_tokens": len(prompt.split()) + 20,
            "cost_usd": 0.0,
            "latency_ms": 50.0,
        }

    async def health_check(self) -> dict:
        return {"provider": self.PROVIDER_TYPE, "status": "healthy", "is_configured": True, "latency_ms": 0.0}


class FallbackRouter:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._events_path = MEMORY_DIR / "fallback_events.json"
        self._providers = [OpenAIProvider(), GeminiProvider(), MockProvider()]

    def _load_events(self) -> list[dict]:
        if not self._events_path.exists():
            return []
        try:
            return json.loads(self._events_path.read_text())
        except Exception:
            return []

    def _save_events(self, data: list[dict]) -> None:
        self._events_path.write_text(json.dumps(data, indent=2, default=str))

    def _log_fallback(self, original: str, fallback: str, reason: str, success: bool) -> None:
        event = FallbackEvent(original_provider=original, fallback_provider=fallback, reason=reason, success=success)
        events = self._load_events()
        events.append(event.model_dump())
        self._save_events(events[-500:])

    def get_provider_chain(self) -> list:
        return self._providers

    def get_active_provider(self) -> object:
        for p in self._providers:
            if p.is_configured():
                return p
        return self._providers[-1]

    async def complete_with_fallback(self, prompt: str, max_tokens: int = 1000, **kwargs) -> dict:
        last_error = ""
        for i, provider in enumerate(self._providers):
            try:
                result = await provider.complete(prompt, max_tokens=max_tokens, **kwargs)
                if result.get("success"):
                    if i > 0:
                        prev = self._providers[i - 1]
                        self._log_fallback(
                            original=prev.PROVIDER_TYPE,
                            fallback=provider.PROVIDER_TYPE,
                            reason=last_error or "previous provider failed",
                            success=True,
                        )
                    return result
                last_error = result.get("error", "unknown error")
            except Exception as e:
                last_error = str(e)
                continue
        return {"success": False, "error": "All providers failed", "last_error": last_error}

    def get_fallback_events(self, limit: int = 20) -> list[dict]:
        return self._load_events()[-limit:]

    def get_last_fallback(self) -> dict | None:
        events = self._load_events()
        return events[-1] if events else None
