from app.decision.models import CONTINUOUS_IMPROVEMENT_AREAS


MISSION_AREA_KEYWORDS = {
    "UI/UX": ["ui", "ux", "dashboard", "product", "experience", "mobile"],
    "SEO": ["seo", "organic", "traffic", "metadata", "keyword"],
    "performance": ["performance", "speed", "loading", "quality"],
    "security": ["security", "cleanup", "api key", "risk"],
    "analytics": ["analytics", "watchlist", "intelligence", "report"],
    "monetization": ["monetization", "growth", "revenue"],
    "branding": ["brand", "branding", "positioning", "messaging"],
    "conversion": ["conversion", "funnel", "landing", "acquisition"],
    "automation": ["automation", "orchestration", "mission", "agent"],
    "scalability": ["scalability", "architecture", "memory", "coordination"],
}


def continuous_focus_areas(project_id: str) -> list[str]:
    if project_id == "yallaplays":
        return ["SEO", "UI/UX", "performance", "monetization", "content", "automation"]

    if project_id == "fionera":
        return ["analytics", "security", "UI/UX", "performance", "automation"]

    if project_id == "mifteh":
        return ["automation", "scalability", "analytics", "developer experience", "security"]

    if project_id == "mifteh-main-site":
        return ["SEO", "UI/UX", "performance", "branding", "analytics", "conversion", "automation", "scalability"]

    return CONTINUOUS_IMPROVEMENT_AREAS


def mission_improvement_areas(mission_id: str, title: str) -> list[str]:
    text = f"{mission_id} {title}".lower()
    areas = [
        area for area, keywords in MISSION_AREA_KEYWORDS.items()
        if any(keyword in text for keyword in keywords)
    ]

    return areas or ["automation", "scalability"]


def priority_from_score(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def effort_label(agent_count: int) -> str:
    if agent_count <= 2:
        return "low"
    if agent_count <= 5:
        return "medium"
    return "high"
