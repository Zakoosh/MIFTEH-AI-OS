from __future__ import annotations
import time
from ..core.config import get_config


class ContentGenerator:
    """Generates real operational content via AI or structured templates.
    Loads keys from .env.local → .env → .env.example via AppConfig."""

    def __init__(self):
        cfg = get_config()
        self._api_key = cfg.openai_api_key
        self._gemini_key = cfg.gemini_api_key
        self._model = cfg.openai_model
        self._gemini_model = getattr(cfg, "gemini_model", "gemini-2.0-flash")
        self._operation_type: str | None = None
        self._project: str | None = None

    def is_ai_available(self) -> bool:
        return bool(self._api_key or self._gemini_key)

    def with_context(self, operation_type: str | None = None, project: str | None = None) -> "ContentGenerator":
        """Set context for analytics tracking."""
        self._operation_type = operation_type
        self._project = project
        return self

    async def generate(self, prompt: str, system_prompt: str = "", max_tokens: int = 2000) -> dict:
        if self._api_key:
            result = await self._generate_openai(prompt, system_prompt, max_tokens)
            self._record(result)
            if result.get("success"):
                return result
        if self._gemini_key:
            result = await self._generate_gemini(prompt, system_prompt, max_tokens)
            self._record(result)
            if result.get("success"):
                return result
        return {"success": False, "error": "All AI providers failed or unconfigured", "provider": "none"}

    def _record(self, result: dict) -> None:
        try:
            from ..services.ai_analytics import record_call
            record_call(
                provider=result.get("provider", "unknown"),
                model=result.get("model", ""),
                success=result.get("success", False),
                prompt_tokens=result.get("prompt_tokens", 0),
                completion_tokens=result.get("completion_tokens", 0),
                cost_usd=result.get("cost_usd", 0.0),
                latency_ms=result.get("latency_ms", 0.0),
                error=result.get("error") if not result.get("success") else None,
                operation_type=self._operation_type,
                project=self._project,
            )
            # Update provider cooldown manager
            from ..scheduler.provider_manager import ProviderCooldownManager
            provider = result.get("provider", "")
            if provider in ("openai", "gemini"):
                pm = ProviderCooldownManager()
                if result.get("success"):
                    pm.record_success(provider)
                elif result.get("error") == "rate_limited":
                    pm.record_rate_limit(provider)
        except Exception:
            pass

    async def _generate_openai(self, prompt: str, system_prompt: str, max_tokens: int) -> dict:
        try:
            import httpx
            start = time.monotonic()
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                    json={"model": self._model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.7},
                )
            latency = (time.monotonic() - start) * 1000
            if resp.status_code == 429:
                return {"success": False, "error": "rate_limited", "provider": "openai", "latency_ms": round(latency, 2)}
            if resp.status_code != 200:
                return {"success": False, "error": f"API {resp.status_code}", "provider": "openai"}
            data = resp.json()
            usage = data.get("usage", {})
            text = data["choices"][0]["message"]["content"] if data.get("choices") else ""
            pt = usage.get("prompt_tokens", 0)
            ct = usage.get("completion_tokens", 0)
            return {
                "success": True, "text": text, "provider": "openai", "model": self._model,
                "prompt_tokens": pt, "completion_tokens": ct,
                "total_tokens": usage.get("total_tokens", pt + ct),
                "cost_usd": round((pt / 1000 * 0.005) + (ct / 1000 * 0.015), 6),
                "latency_ms": round(latency, 2),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "openai"}

    async def _generate_gemini(self, prompt: str, system_prompt: str, max_tokens: int) -> dict:
        try:
            import httpx
            start = time.monotonic()
            combined = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
            model = self._gemini_model.replace("models/", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self._gemini_key}"
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(url, json={
                    "contents": [{"parts": [{"text": combined}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7},
                })
            latency = (time.monotonic() - start) * 1000
            if resp.status_code == 429:
                return {"success": False, "error": "rate_limited", "provider": "gemini", "latency_ms": round(latency, 2)}
            if resp.status_code != 200:
                return {"success": False, "error": f"Gemini {resp.status_code}", "provider": "gemini"}
            data = resp.json()
            candidates = data.get("candidates", [])
            text = candidates[0]["content"]["parts"][0]["text"] if candidates else ""
            usage = data.get("usageMetadata", {})
            pt = usage.get("promptTokenCount", 0)
            ct = usage.get("candidatesTokenCount", 0)
            return {
                "success": True, "text": text, "provider": "gemini", "model": model,
                "prompt_tokens": pt, "completion_tokens": ct, "total_tokens": pt + ct,
                "cost_usd": round((pt / 1000 * 0.00125) + (ct / 1000 * 0.00375), 6),
                "latency_ms": round(latency, 2),
            }
        except Exception as e:
            return {"success": False, "error": str(e), "provider": "gemini"}

    async def generate_structured(self, prompt: str, system_prompt: str = "", max_tokens: int = 2000) -> dict:
        result = await self.generate(prompt, system_prompt, max_tokens)
        if not result.get("success"):
            return result
        import json, re
        text = result["text"]
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", text)
        if json_match:
            try:
                parsed = json.loads(json_match.group(1))
                result["structured"] = parsed
                return result
            except Exception:
                pass
        result["structured"] = {"raw": text}
        return result
