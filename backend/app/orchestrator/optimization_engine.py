from app.orchestrator.models import IMPROVEMENT_AREAS


AREA_WEIGHTS = {
    "security": 10,
    "performance": 8,
    "SEO": 8,
    "UI/UX": 7,
    "analytics": 6,
    "monetization": 6,
    "automation": 7,
    "scalability": 6,
}


def normalize_area(area: str) -> str:
    lower = area.lower()

    if lower == "seo":
        return "SEO"

    if lower in {"ui", "ux", "ui/ux"}:
        return "UI/UX"

    for known in IMPROVEMENT_AREAS:
        if known.lower() == lower:
            return known

    return area


def optimization_score(decision: object) -> int:
    score = round(
        decision.decision_score * 0.45
        + decision.impact_score * 0.25
        + decision.urgency_score * 0.20
        + decision.automation_readiness * 0.10
    )

    normalized_areas = [normalize_area(area) for area in decision.improvement_areas]
    for area in normalized_areas:
        score += AREA_WEIGHTS.get(area, 4)

    if decision.project_id == "mifteh" and decision.mission_id == "improve-dashboard":
        score += 8

    if decision.blocked:
        score -= 18

    return max(0, min(score, 100))


def continuous_areas(decision: object) -> list[str]:
    areas = [normalize_area(area) for area in decision.improvement_areas]

    if not areas:
        areas = ["automation", "scalability"]

    return list(dict.fromkeys(areas))
