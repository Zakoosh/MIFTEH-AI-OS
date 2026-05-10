import json
from datetime import datetime
from pathlib import Path
import re

REPORTS_DIR = Path("app/memory/reports")


def safe_name(value: str):
    return re.sub(r"[^a-zA-Z0-9_-]", "-", value)


def save_agent_report(project_id: str, agent_name: str, content):

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_name(project_id)}_{safe_name(agent_name)}_{timestamp}.json"

    data = {
        "project_id": project_id,
        "agent": agent_name,
        "created_at": datetime.now().isoformat(),
        "report": content
    }

    with open(REPORTS_DIR / filename, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)

    return {
        "file": filename,
        **data
    }


def list_agent_reports():

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    reports = []

    for file in REPORTS_DIR.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            reports.append({
                "file": file.name,
                "project_id": data.get("project_id"),
                "agent": data.get("agent"),
                "created_at": data.get("created_at")
            })
        except Exception:
            pass

    reports.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    return {
        "reports_count": len(reports),
        "reports": reports
    }


def read_agent_report(filename: str):

    file_path = REPORTS_DIR / filename

    if not file_path.exists():
        return {
            "error": "Report not found"
        }

    return json.loads(file_path.read_text(encoding="utf-8"))
