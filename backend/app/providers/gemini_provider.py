from __future__ import annotations
import os
import time


class GeminiProvider:
    PROVIDER_TYPE = "gemini"
    DEFAULT_MODEL = "gemini-1.5-pro"
    COST_PER_1K_INPUT = 0.00125
    COST_PER_1K_OUTPUT = 0.00375

    def __init__(self):
        self._api_key = os.environ.get("GEMINI_API_KEY", "")
        self._model = os.environ.get("GEMINI_MODEL", self.DEFAULT_MODEL)
        self._base_url = "https://generativelanguage.googleapis.com/v1beta"

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
                "error": "GEMINI_API_KEY not configured",
                "provider": self.PROVIDER_TYPE,
                "model": self._model,
            }
        try:
            import httpx
            start = time.monotonic()
            url = f"{self._base_url}/models/{self._model}:generateContent?key={self._api_key}"
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.post(
                    url,
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": temperature},
                    },
                )
            latency_ms = (time.monotonic() - start) * 1000
            if response.status_code != 200:
                return {"success": False, "error": f"API error {response.status_code}", "provider": self.PROVIDER_TYPE, "model": self._model}
            data = response.json()
            candidates = data.get("candidates", [])
            text = candidates[0]["content"]["parts"][0]["text"] if candidates else ""
            usage = data.get("usageMetadata", {})
            prompt_tokens = usage.get("promptTokenCount", 0)
            completion_tokens = usage.get("candidatesTokenCount", 0)
            return {
                "success": True,
                "response": text,
                "provider": self.PROVIDER_TYPE,
                "model": self._model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
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
