from typing import Optional

from app.reports.models import ReportFinding, StructuredReport


PRIORITY_LEVELS = ("critical", "high", "medium", "low")

SCORE_WEIGHTS = {
    "has_summary": 15.0,
    "has_findings": 20.0,
    "has_actions": 25.0,
    "has_risks": 15.0,
    "has_priority": 10.0,
    "is_success": 15.0,
}


def compute_report_score(finding: ReportFinding, success: bool) -> float:
    score = 0.0

    if finding.summary:
        score += SCORE_WEIGHTS["has_summary"]
    if finding.findings:
        score += SCORE_WEIGHTS["has_findings"]
    if finding.actions:
        score += SCORE_WEIGHTS["has_actions"]
    if finding.risks:
        score += SCORE_WEIGHTS["has_risks"]
    if finding.priority in PRIORITY_LEVELS:
        score += SCORE_WEIGHTS["has_priority"]
    if success:
        score += SCORE_WEIGHTS["is_success"]

    return min(score, 100.0)


def normalize_priority(raw: str) -> str:
    cleaned = raw.strip().lower()
    for level in PRIORITY_LEVELS:
        if level in cleaned:
            return level
    return "medium"


def validate_report(report: StructuredReport) -> list[str]:
    issues: list[str] = []

    if not report.report_id:
        issues.append("Missing report_id")
    if not report.project_id:
        issues.append("Missing project_id")
    if not report.agent_name:
        issues.append("Missing agent_name")
    if not report.created_at:
        issues.append("Missing created_at")
    if report.finding.priority not in PRIORITY_LEVELS:
        issues.append(f"Invalid priority: {report.finding.priority}")

    return issues
