import json
from pathlib import Path

from app.automation.models import AutomationHistoryEntry, AutomationTask


AUTOMATION_DIR = Path(__file__).resolve().parent.parent / "memory" / "automation"
TASKS_FILE = AUTOMATION_DIR / "tasks.json"
HISTORY_FILE = AUTOMATION_DIR / "history.json"


def _read_json_list(path: Path) -> list[dict]:
    if not path.is_file():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    return data if isinstance(data, list) else []


def _write_json_list(path: Path, data: list[dict]) -> None:
    AUTOMATION_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def load_tasks() -> list[AutomationTask]:
    tasks: list[AutomationTask] = []

    for item in _read_json_list(TASKS_FILE):
        try:
            tasks.append(AutomationTask.model_validate(item))
        except Exception:
            continue

    return tasks


def save_tasks(tasks: list[AutomationTask]) -> None:
    _write_json_list(TASKS_FILE, [task.model_dump() for task in tasks])


def load_history() -> list[AutomationHistoryEntry]:
    entries: list[AutomationHistoryEntry] = []

    for item in _read_json_list(HISTORY_FILE):
        try:
            entries.append(AutomationHistoryEntry.model_validate(item))
        except Exception:
            continue

    entries.sort(key=lambda entry: entry.started_at or "", reverse=True)
    return entries


def append_history(entry: AutomationHistoryEntry) -> None:
    entries = load_history()
    entries.insert(0, entry)
    _write_json_list(HISTORY_FILE, [item.model_dump() for item in entries])
