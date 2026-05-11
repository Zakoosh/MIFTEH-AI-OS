import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.projects import PROJECTS
from app.engine.report_dashboard import load_all_reports
from app.missions.memory import list_mission_history
from app.missions.planner import list_available_missions


WORKSPACE_ROOT = Path("/workspace").resolve()
AUTOMATION_HISTORY_FILE = WORKSPACE_ROOT / "backend" / "app" / "memory" / "automation" / "history.json"


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)

    return parsed


def _days_since(value: str | None) -> int | None:
    parsed = _parse_datetime(value)
    if parsed is None:
        return None

    return max((datetime.now(timezone.utc) - parsed).days, 0)


def _safe_path_metadata(project_id: str, project: dict[str, Any]) -> dict:
    raw_path = project.get("path", "")
    path = Path(raw_path) if raw_path else Path()
    metadata = {
        "project_id": project_id,
        "name": project.get("name", project_id),
        "project_type": project.get("type", ""),
        "path": str(path) if raw_path else "",
        "path_exists": False,
        "files_count": 0,
        "extensions": {},
        "error": None,
    }

    try:
        if not raw_path:
            metadata["error"] = "Project path is not registered"
            return metadata

        if not path.exists() or not path.is_dir():
            metadata["error"] = "Project path is unavailable"
            return metadata

        files_count = 0
        extensions: dict[str, int] = {}

        for file_path in path.rglob("*"):
            if ".git" in file_path.parts or "__pycache__" in file_path.parts:
                continue

            if not file_path.is_file():
                continue

            files_count += 1
            suffix = file_path.suffix or "no_extension"
            extensions[suffix] = extensions.get(suffix, 0) + 1

            if files_count >= 5000:
                break

        metadata["path_exists"] = True
        metadata["files_count"] = files_count
        metadata["extensions"] = extensions
    except OSError as exc:
        metadata["error"] = str(exc)

    return metadata


def _load_automation_history() -> list[dict]:
    if not AUTOMATION_HISTORY_FILE.is_file():
        return []

    try:
        data = json.loads(AUTOMATION_HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    return data if isinstance(data, list) else []


def _optional_git_state(project_id: str) -> dict:
    try:
        from app.git.status_manager import get_repository_status
    except Exception:
        return {
            "available": False,
            "success": False,
            "error": "Git Automation Layer is not available",
        }

    try:
        status = get_repository_status(project_id)
        data = status.model_dump()
        data["available"] = True
        return data
    except Exception as exc:
        return {
            "available": True,
            "success": False,
            "error": str(exc),
        }


def _project_ids() -> list[str]:
    ids = set(PROJECTS.keys())
    ids.update(mission["project_id"] for mission in list_available_missions())
    return sorted(ids)


def collect_project_profiles() -> list[dict]:
    reports_data = load_all_reports()
    reports = reports_data.get("reports", [])
    mission_history = list_mission_history().model_dump().get("executions", [])
    automation_history = _load_automation_history()
    missions = list_available_missions()

    profiles = []
    for project_id in _project_ids():
        project = PROJECTS.get(project_id, {"name": project_id, "type": "unknown", "path": ""})
        project_reports = [report for report in reports if report.get("project_id") == project_id]
        project_missions = [mission for mission in missions if mission.get("project_id") == project_id]
        project_mission_history = [
            entry for entry in mission_history
            if entry.get("project_id") == project_id
        ]
        project_automation_history = [
            entry for entry in automation_history
            if entry.get("project_id") == project_id
        ]

        latest_dates = [
            item.get("created_at")
            for item in project_reports
            if item.get("created_at")
        ] + [
            item.get("completed_at") or item.get("started_at")
            for item in project_mission_history
            if item.get("completed_at") or item.get("started_at")
        ] + [
            item.get("completed_at") or item.get("started_at")
            for item in project_automation_history
            if item.get("completed_at") or item.get("started_at")
        ]
        latest_dates = [value for value in latest_dates if _parse_datetime(value)]
        latest_activity = max(latest_dates, default=None)

        profiles.append({
            "project_id": project_id,
            "name": project.get("name", project_id),
            "project_type": project.get("type", "unknown"),
            "workspace": _safe_path_metadata(project_id, project),
            "reports": project_reports,
            "broken_reports": reports_data.get("broken_files", []),
            "mission_history": project_mission_history,
            "automation_history": project_automation_history,
            "available_missions": project_missions,
            "git_state": _optional_git_state(project_id),
            "latest_activity": latest_activity,
            "days_since_last_activity": _days_since(latest_activity),
        })

    return profiles


def collect_project_profile(project_id: str) -> dict | None:
    for profile in collect_project_profiles():
        if profile["project_id"] == project_id:
            return profile

    return None
