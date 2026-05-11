from app.intelligence.models import ProjectSignals, ScoreBreakdown


def project_priorities(
    profile: dict,
    signals: ProjectSignals,
    health: ScoreBreakdown,
) -> list[str]:
    priorities: list[str] = []

    if health.risk_score >= 60:
        priorities.append("Reduce project risk")

    if not profile.get("workspace", {}).get("path_exists"):
        priorities.append("Connect or repair workspace path")

    if signals.mission_success_rate and signals.mission_success_rate < 70:
        priorities.append("Improve mission reliability")

    if signals.report_count and signals.report_success_rate < 70:
        priorities.append("Improve report quality and agent execution")

    if health.automation_readiness < 70:
        priorities.append("Prepare project for scheduled automation")

    if signals.days_since_last_activity is None or signals.days_since_last_activity > 30:
        priorities.append("Schedule a fresh improvement mission")

    if signals.git_available and signals.git_clean is False:
        priorities.append("Review uncommitted git changes before automation")

    if not priorities:
        priorities.append("Continue iterative optimization")

    return priorities
