from app.improvements.implementation_plans import build_plan
from app.improvements.models import ImprovementProposal


def yallaplays_ux_proposals(project: str) -> list[ImprovementProposal]:
    proposal = "Add trending games carousel with mobile-first touch targets"
    return [
        ImprovementProposal(
            project=project,
            improvement_type="ux",
            priority="medium",
            proposal=proposal,
            expected_impact=81,
            estimated_effort="medium",
            affected_modules=["homepage", "game_cards", "mobile_nav"],
            rationale=["Improves discovery and mobile engagement"],
            implementation_plan=build_plan(proposal, ["homepage", "game_cards", "mobile_nav"], "medium", 81),
        )
    ]


def fionera_ux_proposals(project: str, missing_features: list[str]) -> list[ImprovementProposal]:
    proposals: list[ImprovementProposal] = []
    for feature in missing_features[:4]:
        proposal = f"Add {feature} visualization"
        proposals.append(ImprovementProposal(
            project=project,
            improvement_type="ux",
            priority="high" if "heatmap" in feature else "medium",
            proposal=proposal,
            expected_impact=76 if "heatmap" in feature else 70,
            estimated_effort="medium",
            affected_modules=["dashboard", "analytics_components", "watchlists"],
            rationale=[f"Missing finance feature detected: {feature}"],
            implementation_plan=build_plan(proposal, ["dashboard", "analytics_components", "watchlists"], "medium", 76),
        ))
    return proposals
