import json
from collections import defaultdict

from app.reports.models import (
    StructuredReport,
    ReportListEntry,
    ReportStats,
    ReportHistoryResponse,
)
from app.reports.storage import list_all_report_files, STRUCTURED_REPORTS_DIR


def _load_report_entry(file_path) -> ReportListEntry | None:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        finding = data.get("finding", {})
        return ReportListEntry(
            report_id=data.get("report_id", file_path.stem),
            mission_id=data.get("mission_id", ""),
            project_id=data.get("project_id", ""),
            agent_name=data.get("agent_name", ""),
            priority=finding.get("priority", "medium"),
            score=finding.get("score", 0.0),
            success=data.get("success", False),
            mode=data.get("mode", "unknown"),
            created_at=data.get("created_at", ""),
        )
    except Exception:
        return None


def get_report_history(
    project_id: str | None = None,
    agent_name: str | None = None,
    limit: int = 50,
) -> ReportHistoryResponse:
    files = list_all_report_files()
    entries: list[ReportListEntry] = []

    for file_path in files:
        entry = _load_report_entry(file_path)
        if entry is None:
            continue

        if project_id and entry.project_id != project_id:
            continue
        if agent_name and entry.agent_name != agent_name:
            continue

        entries.append(entry)

    entries.sort(key=lambda e: e.created_at or "", reverse=True)
    entries = entries[:limit]

    return ReportHistoryResponse(
        total_reports=len(entries),
        reports=entries,
    )


def get_report_stats() -> ReportStats:
    files = list_all_report_files()

    total = 0
    success_count = 0
    failed_count = 0
    total_score = 0.0
    by_project: dict[str, int] = defaultdict(int)
    by_agent: dict[str, int] = defaultdict(int)
    by_priority: dict[str, int] = defaultdict(int)
    by_mode: dict[str, int] = defaultdict(int)

    for file_path in files:
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            continue

        total += 1
        finding = data.get("finding", {})

        if data.get("success", False):
            success_count += 1
        else:
            failed_count += 1

        total_score += finding.get("score", 0.0)
        by_project[data.get("project_id", "unknown")] += 1
        by_agent[data.get("agent_name", "unknown")] += 1
        by_priority[finding.get("priority", "medium")] += 1
        by_mode[data.get("mode", "unknown")] += 1

    average_score = round(total_score / total, 2) if total > 0 else 0.0

    return ReportStats(
        total_reports=total,
        success_count=success_count,
        failed_count=failed_count,
        average_score=average_score,
        by_project=dict(by_project),
        by_agent=dict(by_agent),
        by_priority=dict(by_priority),
        by_mode=dict(by_mode),
    )


def get_latest_reports(limit: int = 10) -> list[ReportListEntry]:
    files = list_all_report_files()
    entries: list[ReportListEntry] = []

    for file_path in files:
        entry = _load_report_entry(file_path)
        if entry is not None:
            entries.append(entry)

    entries.sort(key=lambda e: e.created_at or "", reverse=True)
    return entries[:limit]
