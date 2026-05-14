from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import RuntimeFeedback


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "runtime"


class RuntimeFeedbackSystem:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._path = MEMORY_DIR / "feedback.json"

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        try:
            return json.loads(self._path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._path.write_text(json.dumps(data, indent=2, default=str))

    def record_feedback(self, operation_id: str, feedback_type: str, score: float, details: str = "") -> RuntimeFeedback:
        fb = RuntimeFeedback(operation_id=operation_id, feedback_type=feedback_type, score=max(0.0, min(1.0, score)), details=details)
        data = self._load()
        data.append(fb.model_dump())
        self._save(data[-1000:])
        return fb

    def get_feedback(self, operation_id: str | None = None) -> list[dict]:
        data = self._load()
        if operation_id:
            data = [f for f in data if f.get("operation_id") == operation_id]
        return data

    def compute_avg_score(self, feedback_type: str | None = None) -> float:
        data = self._load()
        if feedback_type:
            data = [f for f in data if f.get("feedback_type") == feedback_type]
        if not data:
            return 0.5
        return round(sum(f.get("score", 0) for f in data) / len(data), 4)

    def should_adapt_behavior(self) -> tuple[bool, str]:
        avg = self.compute_avg_score()
        if avg < 0.3:
            return True, f"Low average feedback score ({avg:.2f}) — consider reducing autonomy"
        if avg > 0.8:
            return False, f"High average feedback score ({avg:.2f}) — behavior is well-calibrated"
        return False, f"Average feedback score ({avg:.2f}) — within acceptable range"
