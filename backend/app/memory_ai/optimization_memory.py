import json
from datetime import datetime, timezone
from pathlib import Path

from app.decision.engine import decision_recommendations
from app.engine.report_dashboard import load_all_reports
from app.intelligence.analyzer import analyze_projects
from app.missions.memory import list_mission_history
from app.orchestrator.telemetry import load_cycles


AUTOMATION_HISTORY_FILE = Path("/workspace/backend/app/memory/automation/history.json")


def _safe_load_json_list(path: Path) -> list[dict]:
    if not path.is_file():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    return data if isinstance(data, list) else []


def _mission_key(project_id: str, mission_id: str) -> str:
    return f"{project_id}::{mission_id}"


def _report_mission_id(report: dict) -> str:
    filename = report.get("file", "")
    project_id = report.get("project_id", "")

    if filename.startswith(project_id + "_"):
        remaining = filename[len(project_id) + 1:]
        parts = remaining.split("_")
        if parts:
            return parts[0]

    return "unknown"


def collect_memory_sources() -> dict:
    reports = load_all_reports().get("reports", [])
    mission_history = list_mission_history().model_dump().get("executions", [])
    automation_history = _safe_load_json_list(AUTOMATION_HISTORY_FILE)
    cycles = load_cycles()
    decisions = decision_recommendations().recommendations
    intelligence_projects = analyze_projects()

    return {
        "reports": reports,
        "mission_history": mission_history,
        "automation_history": automation_history,
        "orchestration_cycles": cycles,
        "decisions": decisions,
        "intelligence_projects": intelligence_projects,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def summarize_mission_effectiveness(sources: dict) -> dict[str, dict]:
    summary: dict[str, dict] = {}

    for report in sources.get("reports", []):
        project_id = report.get("project_id", "unknown")
        mission_id = _report_mission_id(report)
        key = _mission_key(project_id, mission_id)
        item = summary.setdefault(key, {
            "project_id": project_id,
            "mission_id": mission_id,
            "successes": 0,
            "failures": 0,
            "reports": 0,
            "mission_runs": 0,
            "automation_runs": 0,
            "orchestration_recommendations": 0,
            "evidence": [],
        })

        item["reports"] += 1
        if report.get("success"):
            item["successes"] += 1
        else:
            item["failures"] += 1
        item["evidence"].append(f"report:{report.get('file', 'unknown')}")

    for entry in sources.get("mission_history", []):
        project_id = entry.get("project_id", "unknown")
        mission_id = entry.get("mission_id", "unknown")
        key = _mission_key(project_id, mission_id)
        item = summary.setdefault(key, {
            "project_id": project_id,
            "mission_id": mission_id,
            "successes": 0,
            "failures": 0,
            "reports": 0,
            "mission_runs": 0,
            "automation_runs": 0,
            "orchestration_recommendations": 0,
            "evidence": [],
        })

        item["mission_runs"] += 1
        if "fail" in str(entry.get("status", "")).lower():
            item["failures"] += 1
        else:
            item["successes"] += 1
        item["evidence"].append(f"mission:{entry.get('execution_id', 'unknown')}")

    for entry in sources.get("automation_history", []):
        project_id = entry.get("project_id", "unknown")
        mission_id = entry.get("mission_id", "unknown")
        key = _mission_key(project_id, mission_id)
        item = summary.setdefault(key, {
            "project_id": project_id,
            "mission_id": mission_id,
            "successes": 0,
            "failures": 0,
            "reports": 0,
            "mission_runs": 0,
            "automation_runs": 0,
            "orchestration_recommendations": 0,
            "evidence": [],
        })

        item["automation_runs"] += 1
        if "fail" in str(entry.get("status", "")).lower():
            item["failures"] += 1
        else:
            item["successes"] += 1
        item["evidence"].append(f"automation:{entry.get('history_id', 'unknown')}")

    for cycle in sources.get("orchestration_cycles", []):
        for recommendation in cycle.selected_recommendations:
            key = _mission_key(recommendation.project_id, recommendation.mission_id)
            item = summary.setdefault(key, {
                "project_id": recommendation.project_id,
                "mission_id": recommendation.mission_id,
                "successes": 0,
                "failures": 0,
                "reports": 0,
                "mission_runs": 0,
                "automation_runs": 0,
                "orchestration_recommendations": 0,
                "evidence": [],
            })
            item["orchestration_recommendations"] += 1
            item["evidence"].append(f"cycle:{cycle.cycle_id}")

    return summary
