from app.improvements.implementation_plans import build_plan
from app.improvements.models import ImprovementProposal


def yallaplays_monetization_proposals(project: str) -> list[ImprovementProposal]:
    proposal = "Add rewarded placement analytics for high-engagement game categories"
    return [
        ImprovementProposal(
            project=project,
            improvement_type="monetization",
            priority="medium",
            proposal=proposal,
            expected_impact=73,
            estimated_effort="medium",
            affected_modules=["analytics", "game_detail_pages", "category_pages"],
            rationale=["Monetization should follow category engagement signals"],
            implementation_plan=build_plan(proposal, ["analytics", "game_detail_pages", "category_pages"], "medium", 73),
        )
    ]
