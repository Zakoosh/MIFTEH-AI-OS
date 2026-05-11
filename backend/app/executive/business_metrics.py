from app.executive.models import BusinessMetric


def build_business_metrics(strategy_overview: object, memory_snapshot: object, orchestrator_status: object) -> list[BusinessMetric]:
    projects_count = getattr(strategy_overview, "projects_count", 0)
    opportunities_count = getattr(strategy_overview, "opportunities_count", 0)
    portfolio = getattr(strategy_overview, "portfolio", None)
    risks = getattr(portfolio, "portfolio_risks", []) if portfolio else []

    return [
        BusinessMetric(
            name="portfolio_projects",
            value=projects_count,
            trend="stable",
            interpretation="Connected projects under executive portfolio management.",
        ),
        BusinessMetric(
            name="strategic_opportunities",
            value=opportunities_count,
            trend="expanding" if opportunities_count >= projects_count else "watch",
            interpretation="Rule-based growth and optimization opportunities currently visible.",
        ),
        BusinessMetric(
            name="memory_patterns",
            value=len(getattr(memory_snapshot, "patterns", [])),
            trend="learning",
            interpretation="Historical learning signals available for prioritization.",
        ),
        BusinessMetric(
            name="orchestrator_recommendations",
            value=getattr(orchestrator_status, "recommendations_count", 0),
            trend="active" if getattr(orchestrator_status, "recommendations_count", 0) else "watch",
            interpretation="Planning-cycle recommendations captured by the orchestrator.",
        ),
        BusinessMetric(
            name="portfolio_risks",
            value=len(risks),
            trend="risk" if risks else "stable",
            interpretation="Risks that may constrain company-wide execution focus.",
        ),
    ]
