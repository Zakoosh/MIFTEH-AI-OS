from app.intelligence.models import MissionRecommendation, ProjectSignals, ScoreBreakdown


MISSION_KEYWORDS = {
    "security": ["security", "risk", "cleanup", "api key"],
    "performance": ["performance", "speed", "quality", "loading"],
    "seo": ["seo", "organic", "traffic", "metadata"],
    "ux": ["dashboard", "ux", "ui", "product", "experience"],
    "content": ["content", "games", "growth"],
    "automation": ["automation", "orchestration", "mission"],
}


def _priority(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _mission_text(mission: dict) -> str:
    return f"{mission.get('mission_id', '')} {mission.get('title', '')}".lower()


def _has_recent_run(profile: dict, mission_id: str) -> bool:
    for entry in profile.get("mission_history", [])[:5]:
        if entry.get("mission_id") == mission_id:
            return True
    return False


def recommend_for_project(
    profile: dict,
    signals: ProjectSignals,
    health: ScoreBreakdown,
) -> list[MissionRecommendation]:
    recommendations: list[MissionRecommendation] = []

    for mission in profile.get("available_missions", []):
        mission_id = mission.get("mission_id", "")
        text = _mission_text(mission)
        score = 25
        reasons: list[str] = []

        if health.risk_score >= 50:
            score += 20
            reasons.append("Project risk is elevated")

        if health.automation_readiness < 70:
            score += 10
            reasons.append("Automation readiness needs improvement")

        if signals.days_since_last_activity is None or signals.days_since_last_activity > 30:
            score += 20
            reasons.append("Project appears neglected")

        if not _has_recent_run(profile, mission_id):
            score += 15
            reasons.append("Mission has not run recently")

        if signals.report_success_rate and signals.report_success_rate < 70:
            score += 10
            reasons.append("Report success rate is low")

        if any(keyword in text for keyword in MISSION_KEYWORDS["security"]):
            score += 10 if health.risk_score >= 40 else 5
            reasons.append("Security posture should be continuously reviewed")

        if any(keyword in text for keyword in MISSION_KEYWORDS["performance"]):
            score += 8
            reasons.append("Performance is an ongoing optimization area")

        if any(keyword in text for keyword in MISSION_KEYWORDS["seo"]):
            score += 8
            reasons.append("SEO requires continuous improvement")

        if any(keyword in text for keyword in MISSION_KEYWORDS["ux"]):
            score += 6
            reasons.append("UX/UI should keep evolving")

        recommendations.append(MissionRecommendation(
            project_id=profile["project_id"],
            mission_id=mission_id,
            title=mission.get("title", ""),
            priority=_priority(score),
            score=min(score, 100),
            reasons=reasons or ["Continue iterative optimization"],
        ))

    recommendations.sort(key=lambda item: item.score, reverse=True)
    return recommendations


def flatten_recommendations(projects: list) -> list[MissionRecommendation]:
    recommendations: list[MissionRecommendation] = []
    for project in projects:
        recommendations.extend(project.recommendations)

    recommendations.sort(key=lambda item: item.score, reverse=True)
    return recommendations
