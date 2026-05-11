from app.intelligence.models import ProjectIntelligence
from app.intelligence.scoring import build_signals, score_project


def build_health(profile: dict) -> tuple:
    signals = build_signals(profile)
    health = score_project(profile, signals)
    return signals, health


def highest_risk_project(projects: list[ProjectIntelligence]) -> str:
    if not projects:
        return ""

    return max(projects, key=lambda project: project.health.risk_score).project_id


def average_health(projects: list[ProjectIntelligence]) -> int:
    if not projects:
        return 0

    return round(sum(project.health.overall_health for project in projects) / len(projects))


def average_automation_readiness(projects: list[ProjectIntelligence]) -> int:
    if not projects:
        return 0

    return round(sum(project.health.automation_readiness for project in projects) / len(projects))
