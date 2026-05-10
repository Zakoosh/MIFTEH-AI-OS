import json
from pathlib import Path
from collections import defaultdict

REPORTS_DIR = Path("app/memory/reports")


def load_all_reports():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    reports = []
    broken_files = []

    for file in REPORTS_DIR.glob("*.json"):
        try:
            data = json.loads(file.read_text(encoding="utf-8"))
            report = data.get("report", {})

            reports.append({
                "file": file.name,
                "project_id": data.get("project_id", "unknown"),
                "agent": data.get("agent", "unknown"),
                "created_at": data.get("created_at", ""),
                "mode": report.get("mode", "unknown"),
                "success": bool(report.get("success", False)),
                "error": report.get("error"),
                "content_preview": str(report.get("content", ""))[:300]
            })
        except Exception as error:
            broken_files.append({
                "file": file.name,
                "error": str(error)
            })

    reports.sort(key=lambda x: x.get("created_at") or "", reverse=True)

    return {
        "reports": reports,
        "broken_files": broken_files
    }


def reports_dashboard():
    loaded = load_all_reports()
    reports = loaded["reports"]

    by_project = defaultdict(int)
    by_agent = defaultdict(int)
    by_mode = defaultdict(int)
    success_count = 0
    failed_count = 0

    for report in reports:
        by_project[report["project_id"]] += 1
        by_agent[report["agent"]] += 1
        by_mode[report["mode"]] += 1

        if report["success"]:
            success_count += 1
        else:
            failed_count += 1

    return {
        "total_reports": len(reports),
        "success_count": success_count,
        "failed_count": failed_count,
        "broken_files_count": len(loaded["broken_files"]),
        "broken_files": loaded["broken_files"],
        "by_project": dict(by_project),
        "by_agent": dict(by_agent),
        "by_mode": dict(by_mode),
        "latest_reports": reports[:25]
    }


def reports_by_project(project_id: str):
    loaded = load_all_reports()
    reports = loaded["reports"]

    filtered = [
        report for report in reports
        if report["project_id"] == project_id
    ]

    return {
        "project_id": project_id,
        "reports_count": len(filtered),
        "reports": filtered
    }


def reports_by_agent(agent_name: str):
    loaded = load_all_reports()
    reports = loaded["reports"]

    filtered = [
        report for report in reports
        if report["agent"] == agent_name
    ]

    return {
        "agent": agent_name,
        "reports_count": len(filtered),
        "reports": filtered
    }
