from app.improvements.implementation_plans import build_plan
from app.improvements.models import ImprovementProposal


def fionera_analytics_proposals(project: str, analytics_components: list[str]) -> list[ImprovementProposal]:
    proposal = "Add finance insight engagement analytics and watchlist save tracking"
    rationale = ["Measure usage of generated finance insights"]
    if not analytics_components:
        rationale.append("No analytics components detected in repository scan")

    return [
        ImprovementProposal(
            project=project,
            improvement_type="analytics",
            priority="high",
            proposal=proposal,
            expected_impact=79,
            estimated_effort="medium",
            affected_modules=["analytics_pipeline", "watchlist_engine", "dashboard_events"],
            rationale=rationale,
            implementation_plan=build_plan(proposal, ["analytics_pipeline", "watchlist_engine", "dashboard_events"], "medium", 79),
        )
    ]
