from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from typing import Optional

from app.reports.storage import load_report, load_report_raw
from app.reports.history import get_report_history, get_report_stats, get_latest_reports
from app.reports.formatter import format_report

router = APIRouter(prefix="/structured-reports", tags=["structured-reports"])


@router.get("")
def list_reports(
    project_id: Optional[str] = Query(None),
    agent_name: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
):
    return get_report_history(
        project_id=project_id,
        agent_name=agent_name,
        limit=limit,
    ).model_dump()


@router.get("/stats")
def report_stats():
    return get_report_stats().model_dump()


@router.get("/latest")
def latest_reports(limit: int = Query(10, ge=1, le=100)):
    entries = get_latest_reports(limit=limit)
    return {
        "count": len(entries),
        "reports": [e.model_dump() for e in entries],
    }


@router.get("/{report_id}")
def get_report(
    report_id: str,
    output_format: Optional[str] = Query("json", pattern="^(json|markdown|summary)$"),
):
    report = load_report(report_id)

    if report is None:
        return {"error": f"Report '{report_id}' not found"}

    if output_format in ("markdown", "summary"):
        formatted = format_report(report, output_format)
        return PlainTextResponse(content=formatted)

    return load_report_raw(report_id)
