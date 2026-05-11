import json
from datetime import datetime, timezone
from pathlib import Path

from app.execution.models import ExecutionHistoryEntry, ExecutionResult


EXECUTION_DIR = Path("/workspace/backend/app/memory/execution")
HISTORY_FILE = EXECUTION_DIR / "history.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _execution_id(pipeline: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    return f"{pipeline}_{stamp}"


def _read_history() -> list[dict]:
    if not HISTORY_FILE.is_file():
        return []
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return data if isinstance(data, list) else []


def load_history() -> list[ExecutionHistoryEntry]:
    entries = []
    for item in _read_history():
        try:
            entries.append(ExecutionHistoryEntry.model_validate(item))
        except Exception:
            continue
    entries.sort(key=lambda item: item.created_at, reverse=True)
    return entries


def record_execution(result: ExecutionResult) -> ExecutionHistoryEntry:
    EXECUTION_DIR.mkdir(parents=True, exist_ok=True)
    entry = ExecutionHistoryEntry(
        execution_id=_execution_id(result.pipeline),
        pipeline=result.pipeline,
        project_id=result.project_id,
        status=result.status,
        created_at=_now(),
        items_generated=result.items_generated,
        signals_collected=result.signals_collected,
        insights_generated=result.insights_generated,
        validated=result.validated,
        ready_for_apply=result.ready_for_apply,
    )
    entries = load_history()
    entries.insert(0, entry)
    HISTORY_FILE.write_text(
        json.dumps([item.model_dump() for item in entries[:100]], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return entry
