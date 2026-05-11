import json

from app.reports.models import StructuredReport


def format_json(report: StructuredReport) -> str:
    return json.dumps(report.model_dump(), indent=2, ensure_ascii=False, default=str)


def format_markdown(report: StructuredReport) -> str:
    lines: list[str] = []

    lines.append(f"# Report: {report.agent_name}")
    lines.append("")
    lines.append(f"**Project:** {report.project_id}")
    if report.mission_id:
        lines.append(f"**Mission:** {report.mission_id}")
    lines.append(f"**Agent:** {report.agent_name}")
    if report.division:
        lines.append(f"**Division:** {report.division}")
    lines.append(f"**Priority:** {report.finding.priority}")
    lines.append(f"**Score:** {report.finding.score}/100")
    lines.append(f"**Mode:** {report.mode}")
    lines.append(f"**Status:** {'Success' if report.success else 'Failed / Offline'}")
    lines.append(f"**Execution Time:** {report.execution_time}s")
    lines.append(f"**Created:** {report.created_at}")
    lines.append("")

    if report.finding.summary:
        lines.append("## Summary")
        lines.append("")
        lines.append(report.finding.summary)
        lines.append("")

    if report.finding.findings:
        lines.append("## Findings")
        lines.append("")
        for item in report.finding.findings:
            lines.append(f"- {item}")
        lines.append("")

    if report.finding.risks:
        lines.append("## Risks")
        lines.append("")
        for item in report.finding.risks:
            lines.append(f"- {item}")
        lines.append("")

    if report.finding.actions:
        lines.append("## Suggested Actions")
        lines.append("")
        for item in report.finding.actions:
            lines.append(f"- {item}")
        lines.append("")

    if report.error:
        lines.append("## Errors")
        lines.append("")
        lines.append(f"```\n{report.error}\n```")
        lines.append("")

    return "\n".join(lines)


def format_summary(report: StructuredReport) -> str:
    status = "SUCCESS" if report.success else "OFFLINE"
    parts = [
        f"[{status}]",
        f"{report.agent_name}",
        f"({report.division})" if report.division else "",
        f"| project={report.project_id}",
        f"| mission={report.mission_id}" if report.mission_id else "",
        f"| priority={report.finding.priority}",
        f"| score={report.finding.score}",
        f"| time={report.execution_time}s",
    ]
    summary_line = " ".join(p for p in parts if p)

    detail_parts: list[str] = []
    if report.finding.summary:
        detail_parts.append(f"Summary: {report.finding.summary[:150]}")
    if report.finding.findings:
        detail_parts.append(f"Findings: {len(report.finding.findings)} items")
    if report.finding.risks:
        detail_parts.append(f"Risks: {len(report.finding.risks)} items")
    if report.finding.actions:
        detail_parts.append(f"Actions: {len(report.finding.actions)} items")

    if detail_parts:
        return summary_line + "\n  " + " | ".join(detail_parts)

    return summary_line


def format_report(report: StructuredReport, output_format: str = "json") -> str:
    formatters = {
        "json": format_json,
        "markdown": format_markdown,
        "summary": format_summary,
    }

    formatter = formatters.get(output_format, format_json)
    return formatter(report)
