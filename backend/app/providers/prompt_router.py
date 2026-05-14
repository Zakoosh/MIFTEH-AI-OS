from __future__ import annotations
from pathlib import Path
import json
from .models import RoutingRule
from .fallback_router import FallbackRouter


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "providers"

DEFAULT_RULES = [
    RoutingRule(condition="task_type=analysis", target_provider="openai", fallback_provider="gemini", priority=1, description="Analysis tasks go to OpenAI"),
    RoutingRule(condition="task_type=content", target_provider="gemini", fallback_provider="openai", priority=1, description="Content tasks go to Gemini"),
    RoutingRule(condition="task_type=code", target_provider="openai", fallback_provider="gemini", priority=2, description="Code tasks go to OpenAI"),
    RoutingRule(condition="task_type=general", target_provider="openai", fallback_provider="gemini", priority=3, description="General tasks go to OpenAI"),
]


class PromptRouter:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._rules_path = MEMORY_DIR / "routing_rules.json"
        self._fallback = FallbackRouter()
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        if not self._rules_path.exists():
            self._rules_path.write_text(json.dumps([r.model_dump() for r in DEFAULT_RULES], indent=2, default=str))

    def get_rules(self) -> list[dict]:
        try:
            return json.loads(self._rules_path.read_text())
        except Exception:
            return [r.model_dump() for r in DEFAULT_RULES]

    def select_provider(self, task_type: str = "general") -> str:
        rules = sorted(self.get_rules(), key=lambda r: r.get("priority", 99))
        for rule in rules:
            condition = rule.get("condition", "")
            if f"task_type={task_type}" in condition and rule.get("enabled", True):
                return rule.get("target_provider", "openai")
        return "openai"

    async def route(self, prompt: str, task_type: str = "general", max_tokens: int = 1000) -> dict:
        return await self._fallback.complete_with_fallback(prompt, max_tokens=max_tokens, task_type=task_type)

    def get_routing_summary(self) -> dict:
        active = self._fallback.get_active_provider()
        chain = [p.PROVIDER_TYPE for p in self._fallback.get_provider_chain()]
        return {
            "active_provider": active.PROVIDER_TYPE,
            "fallback_chain": chain,
            "routing_rules": self.get_rules(),
            "last_fallback": self._fallback.get_last_fallback(),
        }
