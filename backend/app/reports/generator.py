from datetime import datetime

from app.missions.models import AgentResult
from app.reports.models import StructuredReport, ReportFinding
from app.reports.schemas import compute_report_score, normalize_priority
from app.reports.storage import save_report, generate_report_id


def _calculate_execution_time(started_at: str, completed_at: str) -> float:
    try:
        start = datetime.fromisoformat(started_at)
        end = datetime.fromisoformat(completed_at)
        return round((end - start).total_seconds(), 3)
    except Exception:
        return 0.0


def generate_report_from_agent_result(
    agent_result: AgentResult,
    mission_id: str,
    project_id: str,
) -> StructuredReport:
    finding = ReportFinding(
        summary=agent_result.finding.summary,
        findings=list(agent_result.finding.findings),
        actions=list(agent_result.finding.actions),
        risks=list(agent_result.finding.risks),
        priority=normalize_priority(agent_result.finding.priority),
    )

    score = compute_report_score(finding, agent_result.success)
    finding.score = score

    execution_time = _calculate_execution_time(
        agent_result.started_at or "",
        agent_result.completed_at or "",
    )

    report_id = generate_report_id(project_id, agent_result.agent_name, mission_id)

    report = StructuredReport(
        report_id=report_id,
        mission_id=mission_id,
        project_id=project_id,
        agent_name=agent_result.agent_name,
        division=agent_result.division,
        finding=finding,
        mode=agent_result.mode,
        success=agent_result.success,
        execution_time=execution_time,
        raw_content=agent_result.raw_content,
        error=agent_result.error,
        created_at=datetime.now().isoformat(),
    )

    save_report(report)

    return report


def generate_reports_from_mission(
    agent_results: list[AgentResult],
    mission_id: str,
    project_id: str,
) -> list[StructuredReport]:
    reports: list[StructuredReport] = []

    for agent_result in agent_results:
        report = generate_report_from_agent_result(
            agent_result=agent_result,
            mission_id=mission_id,
            project_id=project_id,
        )
        reports.append(report)

    return reports
