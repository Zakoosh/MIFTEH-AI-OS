from __future__ import annotations
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import json


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "scheduler"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# Backoff windows in seconds after hitting rate limits
COOLDOWN_AFTER_429 = {"openai": 60, "gemini": 30}
# After this many consecutive 429s, switch to template mode
TEMPLATE_FALLBACK_THRESHOLD = 3
# How long template-only mode lasts before trying AI again (seconds)
TEMPLATE_FALLBACK_WINDOW = 3600


class ProviderCooldownManager:
    """Tracks per-provider 429 events and enforces cooldown + template fallback windows."""

    def __init__(self):
        self._state_path = MEMORY_DIR / "provider_state.json"
        self._state = self._load()

    def _load(self) -> dict:
        if not self._state_path.exists():
            return {}
        try:
            return json.loads(self._state_path.read_text())
        except Exception:
            return {}

    def _save(self) -> None:
        self._state_path.write_text(json.dumps(self._state, indent=2, default=str))

    def _provider(self, name: str) -> dict:
        if name not in self._state:
            self._state[name] = {
                "consecutive_429s": 0,
                "cooldown_until": None,
                "template_fallback_until": None,
                "total_429s": 0,
                "last_success": None,
                "last_429": None,
            }
        return self._state[name]

    def is_available(self, provider: str) -> bool:
        now = datetime.utcnow().isoformat()
        p = self._provider(provider)
        cooldown = p.get("cooldown_until")
        if cooldown and cooldown > now:
            return False
        tf = p.get("template_fallback_until")
        if tf and tf > now:
            return False
        return True

    def in_template_fallback(self, provider: str) -> bool:
        now = datetime.utcnow().isoformat()
        p = self._provider(provider)
        tf = p.get("template_fallback_until")
        return bool(tf and tf > now)

    def record_success(self, provider: str) -> None:
        p = self._provider(provider)
        p["consecutive_429s"] = 0
        p["cooldown_until"] = None
        p["last_success"] = datetime.utcnow().isoformat()
        self._save()

    def record_rate_limit(self, provider: str) -> None:
        p = self._provider(provider)
        p["consecutive_429s"] = p.get("consecutive_429s", 0) + 1
        p["total_429s"] = p.get("total_429s", 0) + 1
        p["last_429"] = datetime.utcnow().isoformat()

        cooldown_secs = COOLDOWN_AFTER_429.get(provider, 60)
        p["cooldown_until"] = (datetime.utcnow() + timedelta(seconds=cooldown_secs)).isoformat()

        if p["consecutive_429s"] >= TEMPLATE_FALLBACK_THRESHOLD:
            p["template_fallback_until"] = (datetime.utcnow() + timedelta(seconds=TEMPLATE_FALLBACK_WINDOW)).isoformat()

        self._save()

    def should_use_ai(self) -> bool:
        """Returns True if at least one AI provider is available and not in template fallback."""
        for provider in ("openai", "gemini"):
            if self.is_available(provider) and not self.in_template_fallback(provider):
                return True
        return False

    def get_status(self) -> dict:
        now = datetime.utcnow().isoformat()
        out = {}
        for provider in ("openai", "gemini"):
            p = self._provider(provider)
            cooldown = p.get("cooldown_until")
            tf = p.get("template_fallback_until")
            out[provider] = {
                "available": self.is_available(provider),
                "in_template_fallback": self.in_template_fallback(provider),
                "consecutive_429s": p.get("consecutive_429s", 0),
                "total_429s": p.get("total_429s", 0),
                "cooldown_until": cooldown if (cooldown and cooldown > now) else None,
                "template_fallback_until": tf if (tf and tf > now) else None,
                "last_success": p.get("last_success"),
                "last_429": p.get("last_429"),
            }
        return out
