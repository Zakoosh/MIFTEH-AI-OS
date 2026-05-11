from app.executive.models import CompanyPriority


DOMAIN_KEYWORDS = {
    "growth": ["growth", "lead", "acquisition", "traffic", "portfolio"],
    "conversion": ["conversion", "funnel", "lead", "landing"],
    "SEO": ["seo", "organic", "content", "metadata"],
    "branding": ["brand", "branding", "positioning"],
    "automation": ["automation", "orchestrator", "scheduled", "workflow"],
    "analytics": ["analytics", "dashboard", "metrics", "visibility"],
    "security": ["security", "risk", "trust"],
    "scalability": ["scale", "scaling", "scalability", "architecture"],
}


def _domain_for_text(text: str) -> str:
    lower = text.lower()
    if "optimization" in lower:
        return "growth"

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword.lower() in lower for keyword in keywords):
            return domain
    return "growth"


def _priority_from_scores(urgency: int, impact: int) -> str:
    score = round(urgency * 0.45 + impact * 0.55)
    if score >= 85:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def build_company_priorities(strategy_overview: object) -> list[CompanyPriority]:
    priorities: list[CompanyPriority] = []
    portfolio = getattr(strategy_overview, "portfolio", None)

    for focus in getattr(strategy_overview, "portfolio_focus", [])[:5]:
        domain = _domain_for_text(focus)
        priorities.append(CompanyPriority(
            priority=focus,
            domain=domain,
            urgency=75 if domain in {"growth", "conversion", "SEO"} else 65,
            impact=85 if domain in {"growth", "branding", "automation"} else 70,
            projects=["portfolio"],
        ))

    business_domains = {"growth", "conversion", "SEO", "branding", "automation", "analytics", "scalability"}
    for opportunity in getattr(portfolio, "cross_project_opportunities", []) if portfolio else []:
        if "fail" in opportunity.opportunity.lower():
            continue

        domain = opportunity.domain if opportunity.domain != "optimization" else "growth"
        if domain not in business_domains:
            continue

        urgency = round(opportunity.confidence * 100)
        impact = 85 if opportunity.priority == "high" else 65
        priorities.append(CompanyPriority(
            priority=opportunity.opportunity,
            domain=domain,
            urgency=urgency,
            impact=impact,
            projects=[opportunity.project_id],
        ))

    priorities.sort(key=lambda item: item.urgency * 0.45 + item.impact * 0.55, reverse=True)
    return priorities[:6]


def company_focus(priorities: list[CompanyPriority]) -> str:
    if not priorities:
        return "growth"

    growth_domains = {"growth", "conversion", "SEO", "branding"}
    if any(priority.domain in growth_domains for priority in priorities):
        return "growth"

    domain_scores: dict[str, int] = {}
    for priority in priorities:
        domain_scores[priority.domain] = domain_scores.get(priority.domain, 0) + priority.impact + priority.urgency

    return max(domain_scores, key=domain_scores.get)
