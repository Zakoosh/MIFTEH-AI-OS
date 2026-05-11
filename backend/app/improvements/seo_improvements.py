from app.improvements.implementation_plans import build_plan
from app.improvements.models import ImprovementProposal


def seo_proposals(project: str, seo_gaps: list, missing_categories: list[str] | None = None) -> list[ImprovementProposal]:
    proposals: list[ImprovementProposal] = []
    missing_categories = missing_categories or []

    for category in missing_categories[:4]:
        proposal = f"Create dedicated {category} games category landing page"
        proposals.append(ImprovementProposal(
            project=project,
            improvement_type="seo",
            priority="high",
            proposal=proposal,
            expected_impact=84,
            estimated_effort="medium",
            affected_modules=["homepage", "games_api", "seo_pages"],
            rationale=[f"Missing category detected: {category}", "Category pages improve long-tail search coverage"],
            implementation_plan=build_plan(proposal, ["homepage", "games_api", "seo_pages"], "medium", 84),
        ))

    if seo_gaps:
        proposal = "Add missing SEO titles and meta descriptions to priority pages"
        proposals.append(ImprovementProposal(
            project=project,
            improvement_type="seo",
            priority="high",
            proposal=proposal,
            expected_impact=78,
            estimated_effort="low",
            affected_modules=["seo_pages", "metadata_builder"],
            rationale=[f"{len(seo_gaps)} SEO gaps detected"],
            implementation_plan=build_plan(proposal, ["seo_pages", "metadata_builder"], "low", 78),
        ))

    return proposals
