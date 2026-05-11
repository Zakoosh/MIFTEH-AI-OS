from app.intelligence.models import ProjectSignals, TrendSummary


def _recent_failure_rate(items: list[dict], size: int = 5) -> int:
    recent = items[:size]
    if not recent:
        return 0

    failures = sum(
        1 for item in recent
        if "fail" in str(item.get("status", "")).lower() or item.get("success") is False
    )
    return round((failures / len(recent)) * 100)


def analyze_trend(profile: dict, signals: ProjectSignals) -> TrendSummary:
    mission_history = profile.get("mission_history", [])
    automation_history = profile.get("automation_history", [])
    reports = profile.get("reports", [])
    signals_text: list[str] = []

    recent_failure_rate = max(
        _recent_failure_rate(mission_history),
        _recent_failure_rate(automation_history),
        _recent_failure_rate(reports),
    )

    if recent_failure_rate >= 50:
        failure_trend = "worsening"
        signals_text.append("Recent failure rate is elevated")
    elif recent_failure_rate > 0:
        failure_trend = "watch"
        signals_text.append("Some recent failures detected")
    else:
        failure_trend = "stable"

    neglected = signals.days_since_last_activity is None or signals.days_since_last_activity > 30
    if neglected:
        signals_text.append("Project has limited recent activity")

    if signals.mission_success_rate >= 80 and signals.report_success_rate >= 80:
        direction = "improving"
    elif failure_trend == "worsening" or neglected:
        direction = "needs_attention"
    else:
        direction = "stable"

    return TrendSummary(
        project_id=profile["project_id"],
        direction=direction,
        failure_trend=failure_trend,
        mission_success_rate=signals.mission_success_rate,
        report_success_rate=signals.report_success_rate,
        neglected=neglected,
        signals=signals_text,
    )


def analyze_trends(projects: list) -> list[TrendSummary]:
    return [project.trend for project in projects]
