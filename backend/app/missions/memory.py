import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.missions.models import MissionResult, MissionHistoryEntry, MissionHistorySummary

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
MISSIONS_DIR = _BASE_DIR / "app" / "memory" / "missions"


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", value)


def _generate_execution_id(project_id: str, mission_id: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{_safe_name(project_id)}_{_safe_name(mission_id)}_{timestamp}"


def save_mission_result(result: MissionResult) -> str:
    MISSIONS_DIR.mkdir(parents=True, exist_ok=True)

    execution_id = _generate_execution_id(result.project_id, result.mission_id)
    filename = f"{execution_id}.json"

    data = {
        "execution_id": execution_id,
        **result.model_dump(),
    }

    file_path = MISSIONS_DIR / filename
    file_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    return execution_id


def load_mission_result(execution_id: str) -> Optional[dict]:
    MISSIONS_DIR.mkdir(parents=True, exist_ok=True)

    file_path = MISSIONS_DIR / f"{execution_id}.json"
    if not file_path.is_file():
        return None

    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_mission_history() -> MissionHistorySummary:
    MISSIONS_DIR.mkdir(parents=True, exist_ok=True)

    entries: list[MissionHistoryEntry] = []

    for file_path in MISSIONS_DIR.glob("*.json"):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            entries.append(MissionHistoryEntry(
                execution_id=data.get("execution_id", file_path.stem),
                mission_id=data.get("mission_id", ""),
                project_id=data.get("project_id", ""),
                mission_title=data.get("mission_title", ""),
                status=data.get("status", "unknown"),
                agents_total=data.get("agents_total", 0),
                agents_completed=data.get("agents_completed", 0),
                agents_failed=data.get("agents_failed", 0),
                started_at=data.get("started_at", ""),
                completed_at=data.get("completed_at"),
            ))
        except Exception:
            continue

    entries.sort(key=lambda e: e.started_at or "", reverse=True)

    return MissionHistorySummary(
        total_executions=len(entries),
        executions=entries,
    )
