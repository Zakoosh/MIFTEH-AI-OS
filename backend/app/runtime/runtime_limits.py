from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import json
from .models import RuntimeLimit


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "runtime"

MAX_OPS_PER_HOUR = 50
MAX_COST_PER_DAY_USD = 10.0
MIN_TRUST_SCORE = 0.3
MAX_CYCLES_PER_DAY = 100


class RuntimeLimits:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._path = MEMORY_DIR / "limits.json"
        self._ops_path = MEMORY_DIR / "ops_ledger.json"

    def _load_limits(self) -> list[dict]:
        if not self._path.exists():
            return self._default_limits()
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return self._default_limits()

    def _save_limits(self, data: list[dict]) -> None:
        self._path.write_text(json.dumps(data, indent=2, default=str))

    def _default_limits(self) -> list[dict]:
        return [
            RuntimeLimit(limit_type="ops_per_hour", max_value=MAX_OPS_PER_HOUR, period="hourly").model_dump(),
            RuntimeLimit(limit_type="cost_per_day_usd", max_value=MAX_COST_PER_DAY_USD, period="daily").model_dump(),
            RuntimeLimit(limit_type="cycles_per_day", max_value=MAX_CYCLES_PER_DAY, period="daily").model_dump(),
        ]

    def _load_ops(self) -> list[dict]:
        if not self._ops_path.exists():
            return []
        try:
            return json.loads(self._ops_path.read_text())
        except Exception:
            return []

    def _save_ops(self, data: list[dict]) -> None:
        self._ops_path.write_text(json.dumps(data, indent=2, default=str))

    def record_operation(self, op_id: str, cost: float = 0.0) -> None:
        ops = self._load_ops()
        ops.append({"id": op_id, "cost": cost, "timestamp": datetime.utcnow().isoformat()})
        self._save_ops(ops[-5000:])

    def count_ops_last_hour(self) -> int:
        cutoff = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        return len([o for o in self._load_ops() if o.get("timestamp", "") >= cutoff])

    def cost_today(self) -> float:
        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        return round(sum(o.get("cost", 0) for o in self._load_ops() if o.get("timestamp", "") >= cutoff), 6)

    def cycles_today(self) -> int:
        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        return len([o for o in self._load_ops() if o.get("timestamp", "") >= cutoff and o.get("is_cycle")])

    def check_trust_score(self, trust_score: float) -> tuple[bool, str]:
        if trust_score < MIN_TRUST_SCORE:
            return False, f"Trust score {trust_score:.2f} below minimum {MIN_TRUST_SCORE}"
        return True, "ok"

    def check_ops_limit(self) -> tuple[bool, str]:
        count = self.count_ops_last_hour()
        if count >= MAX_OPS_PER_HOUR:
            return False, f"Ops per hour limit reached ({count}/{MAX_OPS_PER_HOUR})"
        return True, "ok"

    def check_cost_limit(self, estimated_cost: float = 0.0) -> tuple[bool, str]:
        today = self.cost_today()
        if today + estimated_cost > MAX_COST_PER_DAY_USD:
            return False, f"Daily cost limit would be exceeded (${today:.4f}/${MAX_COST_PER_DAY_USD})"
        return True, "ok"

    def can_execute(self, trust_score: float, estimated_cost: float = 0.0) -> tuple[bool, str]:
        for check_fn, args in [
            (self.check_trust_score, (trust_score,)),
            (self.check_ops_limit, ()),
            (self.check_cost_limit, (estimated_cost,)),
        ]:
            ok, reason = check_fn(*args)
            if not ok:
                return False, reason
        return True, "ok"

    def get_limits_status(self) -> list[dict]:
        return [
            {
                "limit_type": "ops_per_hour",
                "max_value": MAX_OPS_PER_HOUR,
                "current_value": self.count_ops_last_hour(),
                "exceeded": self.count_ops_last_hour() >= MAX_OPS_PER_HOUR,
            },
            {
                "limit_type": "cost_per_day_usd",
                "max_value": MAX_COST_PER_DAY_USD,
                "current_value": self.cost_today(),
                "exceeded": self.cost_today() >= MAX_COST_PER_DAY_USD,
            },
            {
                "limit_type": "min_trust_score",
                "max_value": 1.0,
                "current_value": MIN_TRUST_SCORE,
                "exceeded": False,
                "note": f"Minimum required: {MIN_TRUST_SCORE}",
            },
        ]
