from __future__ import annotations
import json
from datetime import datetime, date
from pathlib import Path
from typing import Any

MEMORY_DIR = Path(__file__).parent.parent / "memory" / "analytics"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)
_CALLS_PATH = MEMORY_DIR / "ai_calls.json"


def _load() -> list[dict]:
    if not _CALLS_PATH.exists():
        return []
    try:
        return json.loads(_CALLS_PATH.read_text())
    except Exception:
        return []


def _save(data: list[dict]) -> None:
    # Keep last 10,000 calls
    _CALLS_PATH.write_text(json.dumps(data[-10000:], indent=2, default=str))


def record_call(
    provider: str,
    model: str,
    success: bool,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    cost_usd: float = 0.0,
    latency_ms: float = 0.0,
    error: str | None = None,
    operation_type: str | None = None,
    project: str | None = None,
) -> None:
    data = _load()
    data.append({
        "ts": datetime.utcnow().isoformat(),
        "date": date.today().isoformat(),
        "provider": provider,
        "model": model,
        "success": success,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens,
        "cost_usd": cost_usd,
        "latency_ms": latency_ms,
        "error": error,
        "operation_type": operation_type,
        "project": project,
    })
    _save(data)


def get_analytics(days: int = 7) -> dict:
    data = _load()
    if not data:
        return _empty_analytics()

    cutoff = None
    if days:
        from datetime import timedelta
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        data = [c for c in data if c.get("ts", "") >= cutoff]

    if not data:
        return _empty_analytics()

    by_provider: dict[str, dict] = {}
    by_day: dict[str, dict] = {}
    by_project: dict[str, int] = {}
    by_op_type: dict[str, int] = {}
    total_cost = 0.0
    total_tokens = 0
    success_count = 0
    rate_limited = 0

    for c in data:
        p = c.get("provider", "unknown")
        if p not in by_provider:
            by_provider[p] = {"requests": 0, "success": 0, "tokens": 0, "cost_usd": 0.0, "latency_ms_total": 0.0, "errors": 0}
        bp = by_provider[p]
        bp["requests"] += 1
        if c.get("success"):
            bp["success"] += 1
            success_count += 1
        else:
            bp["errors"] += 1
            if c.get("error") == "rate_limited":
                rate_limited += 1
        bp["tokens"] += c.get("total_tokens", 0)
        bp["cost_usd"] += c.get("cost_usd", 0.0)
        bp["latency_ms_total"] += c.get("latency_ms", 0.0)
        total_cost += c.get("cost_usd", 0.0)
        total_tokens += c.get("total_tokens", 0)

        d = c.get("date", "unknown")
        if d not in by_day:
            by_day[d] = {"requests": 0, "success": 0, "cost_usd": 0.0, "tokens": 0}
        by_day[d]["requests"] += 1
        if c.get("success"):
            by_day[d]["success"] += 1
        by_day[d]["cost_usd"] += c.get("cost_usd", 0.0)
        by_day[d]["tokens"] += c.get("total_tokens", 0)

        proj = c.get("project") or "unknown"
        by_project[proj] = by_project.get(proj, 0) + 1

        ot = c.get("operation_type") or "unknown"
        by_op_type[ot] = by_op_type.get(ot, 0) + 1

    for p, stats in by_provider.items():
        if stats["success"] > 0:
            stats["avg_latency_ms"] = round(stats["latency_ms_total"] / stats["success"], 1)
        else:
            stats["avg_latency_ms"] = 0.0
        stats.pop("latency_ms_total", None)
        stats["success_rate"] = round(stats["success"] / stats["requests"] * 100, 1) if stats["requests"] else 0.0
        stats["cost_usd"] = round(stats["cost_usd"], 6)

    total = len(data)
    return {
        "period_days": days,
        "total_calls": total,
        "successful_calls": success_count,
        "success_rate_pct": round(success_count / total * 100, 1) if total else 0.0,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "rate_limited_calls": rate_limited,
        "ai_generated_pct": round(success_count / max(total, 1) * 100, 1),
        "by_provider": by_provider,
        "by_day": dict(sorted(by_day.items())[-7:]),
        "by_project": by_project,
        "by_operation_type": by_op_type,
    }


def _empty_analytics() -> dict:
    return {
        "period_days": 7,
        "total_calls": 0,
        "successful_calls": 0,
        "success_rate_pct": 0.0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "rate_limited_calls": 0,
        "ai_generated_pct": 0.0,
        "by_provider": {},
        "by_day": {},
        "by_project": {},
        "by_operation_type": {},
    }
