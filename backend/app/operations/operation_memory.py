from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import OperationalOutput, OperationalPreview, OperationBatch


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "operations"


class OperationMemory:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._outputs_path = MEMORY_DIR / "outputs.json"
        self._previews_path = MEMORY_DIR / "previews.json"
        self._batches_path = MEMORY_DIR / "batches.json"

    def _load(self, path: Path) -> list[dict]:
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except Exception:
            return []

    def _save(self, path: Path, data: list[dict]) -> None:
        path.write_text(json.dumps(data, indent=2, default=str))

    def save_output(self, output: OperationalOutput) -> None:
        data = self._load(self._outputs_path)
        for i, o in enumerate(data):
            if o["id"] == output.id:
                data[i] = output.model_dump()
                self._save(self._outputs_path, data)
                return
        data.append(output.model_dump())
        self._save(self._outputs_path, data[-5000:])

    def save_preview(self, preview: OperationalPreview) -> None:
        data = self._load(self._previews_path)
        for i, p in enumerate(data):
            if p["id"] == preview.id:
                data[i] = preview.model_dump()
                self._save(self._previews_path, data)
                return
        data.append(preview.model_dump())
        self._save(self._previews_path, data[-2000:])

    def save_batch(self, batch: OperationBatch) -> None:
        data = self._load(self._batches_path)
        for i, b in enumerate(data):
            if b["id"] == batch.id:
                data[i] = batch.model_dump()
                self._save(self._batches_path, data)
                return
        data.append(batch.model_dump())
        self._save(self._batches_path, data[-500:])

    def get_outputs(self, project: str | None = None, output_type: str | None = None, status: str | None = None, limit: int = 100) -> list[dict]:
        data = self._load(self._outputs_path)
        if project:
            data = [o for o in data if o.get("project") == project]
        if output_type:
            data = [o for o in data if o.get("output_type") == output_type]
        if status:
            data = [o for o in data if o.get("status") == status]
        return data[-limit:]

    def get_output(self, output_id: str) -> dict | None:
        for o in self._load(self._outputs_path):
            if o["id"] == output_id:
                return o
        return None

    def get_preview(self, preview_id: str) -> dict | None:
        for p in self._load(self._previews_path):
            if p["id"] == preview_id:
                return p
        return None

    def get_preview_for_output(self, output_id: str) -> dict | None:
        for p in self._load(self._previews_path):
            if p.get("output_id") == output_id:
                return p
        return None

    def update_output_status(self, output_id: str, status: str, extra: dict | None = None) -> bool:
        data = self._load(self._outputs_path)
        for o in data:
            if o["id"] == output_id:
                o["status"] = status
                o["updated_at"] = datetime.utcnow().isoformat()
                if extra:
                    o.update(extra)
                self._save(self._outputs_path, data)
                return True
        return False

    def get_analytics(self, project: str | None = None) -> dict:
        data = self._load(self._outputs_path)
        if project:
            data = [o for o in data if o.get("project") == project]
        by_type: dict[str, int] = {}
        by_status: dict[str, int] = {}
        for o in data:
            t = o.get("output_type", "unknown")
            s = o.get("status", "unknown")
            by_type[t] = by_type.get(t, 0) + 1
            by_status[s] = by_status.get(s, 0) + 1
        return {
            "total_outputs": len(data),
            "by_type": by_type,
            "by_status": by_status,
            "applied_count": by_status.get("applied", 0),
            "pending_count": by_status.get("generated", 0) + by_status.get("previewed", 0),
            "total_cost_usd": round(sum(o.get("cost_usd", 0) for o in data), 6),
            "ai_generated_count": len([o for o in data if o.get("ai_generated")]),
        }
