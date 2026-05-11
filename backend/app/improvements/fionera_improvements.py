from app.improvements.analytics_improvements import fionera_analytics_proposals
from app.improvements.ux_improvements import fionera_ux_proposals
from app.integration.fionera_sync import sync_fionera


def build_fionera_improvements() -> list:
    integration = sync_fionera()
    proposals = []
    proposals.extend(fionera_ux_proposals("fionera", integration.missing_features))
    proposals.extend(fionera_analytics_proposals("fionera", integration.analytics_components))

    if integration.watchlists_detected == 0:
        from app.improvements.implementation_plans import build_plan
        from app.improvements.models import ImprovementProposal
        proposal = "Create watchlist scoring and priority ranking module"
        proposals.append(ImprovementProposal(
            project="fionera",
            improvement_type="watchlist",
            priority="high",
            proposal=proposal,
            expected_impact=77,
            estimated_effort="medium",
            affected_modules=["watchlist_engine", "market_data", "dashboard"],
            rationale=["No watchlist structure detected", "Watchlists are core finance workflow"],
            implementation_plan=build_plan(proposal, ["watchlist_engine", "market_data", "dashboard"], "medium", 77),
        ))

    proposals.sort(key=lambda item: item.expected_impact, reverse=True)
    return proposals
