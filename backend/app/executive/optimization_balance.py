from app.executive.models import OptimizationBalance


def build_optimization_balance(strategy_overview: object, priorities: list, resource_distribution: dict[str, int]) -> OptimizationBalance:
    domains = [priority.domain for priority in priorities]
    growth_focus = sum(1 for domain in domains if domain in {"growth", "SEO", "conversion", "branding"})
    automation_focus = sum(1 for domain in domains if domain == "automation")
    risk_focus = sum(1 for domain in domains if domain in {"security", "risk"})
    stability_focus = sum(1 for domain in domains if domain in {"analytics", "scalability", "security"})
    notes = []

    if resource_distribution.get("mifteh-main-site", 0) >= 30:
        notes.append("Business acquisition layer receives primary focus.")

    if growth_focus > stability_focus + 3:
        notes.append("Growth-heavy plan should keep operational safeguards visible.")

    if automation_focus == 0:
        notes.append("Add automation-focused executive tracking to sustain scale.")

    if not notes:
        notes.append("Portfolio focus is balanced across growth, stability, and automation.")

    total = max(len(domains), 1)
    return OptimizationBalance(
        growth_focus=round(growth_focus / total * 100),
        stability_focus=round(stability_focus / total * 100),
        automation_focus=round(automation_focus / total * 100),
        risk_focus=round(risk_focus / total * 100),
        balance_notes=notes,
    )
