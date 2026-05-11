from app.intelligence.models import ProjectSignals, ScoreBreakdown


def _percentage(successes: int, total: int) -> int:
    if total <= 0:
        return 0
    return round((successes / total) * 100)


def _bounded(value: int) -> int:
    return max(0, min(100, value))


def build_signals(profile: dict) -> ProjectSignals:
    mission_history = profile.get("mission_history", [])
    reports = profile.get("reports", [])
    automation_history = profile.get("automation_history", [])
    git_state = profile.get("git_state", {})

    mission_runs = len(mission_history)
    mission_failures = sum(
        1 for item in mission_history
        if "fail" in str(item.get("status", "")).lower()
    )
    mission_successes = mission_runs - mission_failures

    report_count = len(reports)
    report_successes = sum(1 for report in reports if report.get("success"))
    report_failures = report_count - report_successes

    automation_runs = len(automation_history)
    automation_failures = sum(
        1 for item in automation_history
        if "fail" in str(item.get("status", "")).lower()
    )

    return ProjectSignals(
        mission_runs=mission_runs,
        mission_successes=mission_successes,
        mission_failures=mission_failures,
        mission_success_rate=_percentage(mission_successes, mission_runs),
        report_count=report_count,
        report_successes=report_successes,
        report_failures=report_failures,
        report_success_rate=_percentage(report_successes, report_count),
        automation_runs=automation_runs,
        automation_failures=automation_failures,
        available_missions=len(profile.get("available_missions", [])),
        days_since_last_activity=profile.get("days_since_last_activity"),
        git_clean=git_state.get("is_clean") if git_state.get("success") else None,
        git_available=bool(git_state.get("available")),
    )


def score_project(profile: dict, signals: ProjectSignals) -> ScoreBreakdown:
    workspace = profile.get("workspace", {})
    path_score = 100 if workspace.get("path_exists") else 35

    reliability_inputs = []
    if signals.mission_runs:
        reliability_inputs.append(signals.mission_success_rate)
    if signals.report_count:
        reliability_inputs.append(signals.report_success_rate)
    if signals.automation_runs:
        automation_successes = signals.automation_runs - signals.automation_failures
        reliability_inputs.append(_percentage(automation_successes, signals.automation_runs))

    reliability_score = round(sum(reliability_inputs) / len(reliability_inputs)) if reliability_inputs else 65

    days_since_activity = signals.days_since_last_activity
    if days_since_activity is None:
        activity_score = 30
    elif days_since_activity <= 7:
        activity_score = 100
    elif days_since_activity <= 30:
        activity_score = 75
    elif days_since_activity <= 90:
        activity_score = 50
    else:
        activity_score = 25

    git_score = 75
    if signals.git_available and signals.git_clean is True:
        git_score = 100
    elif signals.git_available and signals.git_clean is False:
        git_score = 55

    mission_score = 100 if signals.available_missions else 40

    overall_health = _bounded(round(
        path_score * 0.20
        + reliability_score * 0.35
        + activity_score * 0.20
        + git_score * 0.10
        + mission_score * 0.15
    ))

    automation_readiness = _bounded(round(
        mission_score * 0.35
        + path_score * 0.20
        + reliability_score * 0.25
        + git_score * 0.20
    ))

    risk_score = _bounded(100 - overall_health)

    if signals.mission_failures:
        risk_score = _bounded(risk_score + min(signals.mission_failures * 5, 20))

    if signals.automation_failures:
        risk_score = _bounded(risk_score + min(signals.automation_failures * 5, 15))

    return ScoreBreakdown(
        overall_health=overall_health,
        risk_score=risk_score,
        automation_readiness=automation_readiness,
        reliability_score=_bounded(reliability_score),
        activity_score=_bounded(activity_score),
    )
