import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.reports.models import StructuredReport

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
STRUCTURED_REPORTS_DIR = _BASE_DIR / "app" / "memory" / "structured_reports"


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", value)


def generate_report_id(project_id: str, agent_name: str, mission_id: str = "") -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    parts = [_safe_name(project_id)]
    if mission_id:
        parts.append(_safe_name(mission_id))
    parts.append(_safe_name(agent_name))
    parts.append(timestamp)
    return "_".join(parts)


def save_report(report: StructuredReport) -> str:
    STRUCTURED_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    report_id = report.report_id
    if not report_id:
        report_id = generate_report_id(
            report.project_id, report.agent_name, report.mission_id,
        )
        report.report_id = report_id

    filename = f"{report_id}.json"
    file_path = STRUCTURED_REPORTS_DIR / filename

    file_path.write_text(
        json.dumps(report.model_dump(), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    return report_id


def load_report(report_id: str) -> Optional[StructuredReport]:
    STRUCTURED_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    file_path = STRUCTURED_REPORTS_DIR / f"{report_id}.json"
    if not file_path.is_file():
        return None

    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return StructuredReport(**data)
    except Exception:
        return None


def load_report_raw(report_id: str) -> Optional[dict]:
    STRUCTURED_REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    file_path = STRUCTURED_REPORTS_DIR / f"{report_id}.json"
    if not file_path.is_file():
        return None

    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception:
        return None


def list_all_report_files() -> list[Path]:
    STRUCTURED_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    return sorted(STRUCTURED_REPORTS_DIR.glob("*.json"), reverse=True)


def delete_report(report_id: str) -> bool:
    file_path = STRUCTURED_REPORTS_DIR / f"{report_id}.json"
    if file_path.is_file():
        file_path.unlink()
        return True
    return False
