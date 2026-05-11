from app.improvements.monetization import yallaplays_monetization_proposals
from app.improvements.seo_improvements import seo_proposals
from app.improvements.ux_improvements import yallaplays_ux_proposals
from app.integration.yallaplays_sync import sync_yallaplays


def build_yallaplays_improvements() -> list:
    integration = sync_yallaplays()
    proposals = []
    proposals.extend(seo_proposals("yallaplays", integration.seo_gaps, integration.missing_categories))
    proposals.extend(yallaplays_ux_proposals("yallaplays"))
    proposals.extend(yallaplays_monetization_proposals("yallaplays"))

    if integration.metadata_gaps:
        proposal = "Build game metadata completion workflow"
        from app.improvements.implementation_plans import build_plan
        from app.improvements.models import ImprovementProposal
        proposals.append(ImprovementProposal(
            project="yallaplays",
            improvement_type="content",
            priority="medium",
            proposal=proposal,
            expected_impact=74,
            estimated_effort="low",
            affected_modules=["metadata_builder", "content_pipeline"],
            rationale=integration.metadata_gaps,
            implementation_plan=build_plan(proposal, ["metadata_builder", "content_pipeline"], "low", 74),
        ))

    proposals.sort(key=lambda item: item.expected_impact, reverse=True)
    return proposals
