from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import json
from .models import ProviderRequest, CostSummary


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "providers"
DAILY_BUDGET_USD = 10.0


class CostTracking:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._requests_path = MEMORY_DIR / "requests.json"

    def _load(self) -> list[dict]:
        if not self._requests_path.exists():
            return []
        try:
            return json.loads(self._requests_path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._requests_path.write_text(json.dumps(data, indent=2, default=str))

    def record_request(self, request: ProviderRequest) -> None:
        data = self._load()
        data.append(request.model_dump())
        self._save(data[-10000:])

    def get_daily_cost(self) -> float:
        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        data = self._load()
        return round(sum(r.get("cost_usd", 0) for r in data if r.get("created_at", "") >= cutoff), 6)

    def get_budget_remaining(self) -> float:
        return max(0.0, round(DAILY_BUDGET_USD - self.get_daily_cost(), 6))

    def is_within_budget(self, estimated_cost: float = 0.0) -> bool:
        return self.get_daily_cost() + estimated_cost <= DAILY_BUDGET_USD

    def get_summary(self, period: str = "24h") -> dict:
        hours = {"24h": 24, "7d": 168, "30d": 720}.get(period, 24)
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        data = [r for r in self._load() if r.get("created_at", "") >= cutoff]

        by_provider: dict[str, dict] = {}
        for r in data:
            p = r.get("provider", "unknown")
            if p not in by_provider:
                by_provider[p] = {"requests": 0, "tokens": 0, "cost": 0.0}
            by_provider[p]["requests"] += 1
            by_provider[p]["tokens"] += r.get("total_tokens", 0)
            by_provider[p]["cost"] += r.get("cost_usd", 0)

        return {
            "period": period,
            "total_requests": len(data),
            "total_tokens": sum(r.get("total_tokens", 0) for r in data),
            "total_cost_usd": round(sum(r.get("cost_usd", 0) for r in data), 6),
            "by_provider": [{"provider": k, **v} for k, v in by_provider.items()],
            "budget_remaining_usd": self.get_budget_remaining(),
            "daily_budget_usd": DAILY_BUDGET_USD,
            "generated_at": datetime.utcnow().isoformat(),
        }

    def get_requests(self, provider: str | None = None, limit: int = 50) -> list[dict]:
        data = self._load()
        if provider:
            data = [r for r in data if r.get("provider") == provider]
        return data[-limit:]
