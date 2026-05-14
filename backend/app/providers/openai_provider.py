from __future__ import annotations
import os
import time
from datetime import datetime


class OpenAIProvider:
    PROVIDER_TYPE = "openai"
    DEFAULT_MODEL = "gpt-4o"
    COST_PER_1K_INPUT = 0.005
    COST_PER_1K_OUTPUT = 0.015

    def __init__(self):
        self._api_key = os.environ.get("OPENAI_API_KEY", "")
        self._model = os.environ.get("OPENAI_MODEL", self.DEFAULT_MODEL)

    def is_configured(self) -> bool:
        return bool(self._api_key)

    def get_cost_estimate(self, input_tokens: int, output_tokens: int = 0) -> float:
        return round(
            (input_tokens / 1000) * self.COST_PER_1K_INPUT + (output_tokens / 1000) * self.COST_PER_1K_OUTPUT,
            6,
        )

    async def complete(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7, **kwargs) -> dict:
        if not self.is_configured():
            return {
                "success": False,
                "error": "OPENAI_API_KEY not configured",
                "provider": self.PROVIDER_TYPE,
                "model": self._model,
            }
        try:
            import httpx
            start = time.monotonic()
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json={
                        "model": self._model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                )
            latency_ms = (time.monotonic() - start) * 1000
            if response.status_code != 200:
                return {"success": False, "error": f"API error {response.status_code}", "provider": self.PROVIDER_TYPE, "model": self._model}
            data = response.json()
            usage = data.get("usage", {})
            text = data["choices"][0]["message"]["content"] if data.get("choices") else ""
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            return {
                "success": True,
                "response": text,
                "provider": self.PROVIDER_TYPE,
                "model": self._model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": usage.get("total_tokens", prompt_tokens + completion_tokens),
                "cost_usd": self.get_cost_estimate(prompt_tokens, completion_tokens),
                "latency_ms": round(latency_ms, 2),
            }
        except ImportError:
            return {"success": False, "error": "httpx not installed", "provider": self.PROVIDER_TYPE, "model": self._model}
        except Exception as e:
            return {"success": False, "error": str(e), "provider": self.PROVIDER_TYPE, "model": self._model}

    async def health_check(self) -> dict:
        if not self.is_configured():
            return {"provider": self.PROVIDER_TYPE, "status": "unavailable", "reason": "API key not configured", "is_configured": False}
        try:
            result = await self.complete("ping", max_tokens=5)
            return {
                "provider": self.PROVIDER_TYPE,
                "model": self._model,
                "status": "healthy" if result["success"] else "degraded",
                "is_configured": True,
                "latency_ms": result.get("latency_ms", 0),
            }
        except Exception as e:
            return {"provider": self.PROVIDER_TYPE, "status": "unavailable", "error": str(e), "is_configured": True}
