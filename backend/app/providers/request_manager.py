from __future__ import annotations
import asyncio
import time
from datetime import datetime
from pathlib import Path
from .models import ProviderRequest
from .prompt_router import PromptRouter
from .cost_tracking import CostTracking


class RequestManager:
    MAX_RETRIES = 3
    RETRY_BACKOFF = [1.0, 2.0, 4.0]

    def __init__(self):
        self._router = PromptRouter()
        self._costs = CostTracking()

    async def execute(self, prompt: str, task_type: str = "general", max_tokens: int = 1000, **kwargs) -> dict:
        if not self._costs.is_within_budget(estimated_cost=0.01):
            return {
                "success": False,
                "error": "Daily budget exceeded",
                "budget_remaining": self._costs.get_budget_remaining(),
            }

        last_error = ""
        for attempt in range(self.MAX_RETRIES):
            try:
                start = time.monotonic()
                result = await self._router.route(prompt, task_type=task_type, max_tokens=max_tokens)
                latency_ms = (time.monotonic() - start) * 1000

                request_record = ProviderRequest(
                    provider=result.get("provider", "unknown"),
                    model=result.get("model", "unknown"),
                    prompt_tokens=result.get("prompt_tokens", 0),
                    completion_tokens=result.get("completion_tokens", 0),
                    total_tokens=result.get("total_tokens", 0),
                    cost_usd=result.get("cost_usd", 0.0),
                    latency_ms=round(latency_ms, 2),
                    success=result.get("success", False),
                    error=result.get("error"),
                    task_type=task_type,
                )
                self._costs.record_request(request_record)

                if result.get("success"):
                    return result

                last_error = result.get("error", "unknown")
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_BACKOFF[attempt])

            except Exception as e:
                last_error = str(e)
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_BACKOFF[attempt])

        return {"success": False, "error": f"All retries failed: {last_error}"}

    def get_routing_info(self) -> dict:
        return self._router.get_routing_summary()

    def get_cost_summary(self, period: str = "24h") -> dict:
        return self._costs.get_summary(period)
