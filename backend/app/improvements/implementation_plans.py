from app.improvements.models import ImplementationPlan


def build_plan(
    proposal: str,
    affected_modules: list[str],
    estimated_effort: str,
    estimated_impact: int,
) -> ImplementationPlan:
    return ImplementationPlan(
        proposal=proposal,
        affected_modules=affected_modules,
        estimated_effort=estimated_effort,
        estimated_impact=estimated_impact,
        steps=[
            "Review repository intelligence and confirm affected modules",
            "Generate preview patch or implementation checklist",
            "Validate SEO/UX/analytics impact in staging or preview mode",
            "Apply only after manual approval",
        ],
        validation_checks=[
            "No destructive file operations",
            "No production deployment",
            "Preview is reviewed before apply",
            "Relevant dashboard/API smoke checks pass",
        ],
    )
