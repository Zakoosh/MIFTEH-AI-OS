from app.improvements.fionera_improvements import build_fionera_improvements
from app.improvements.models import ImprovementCollection, ImprovementRoadmap, RoadmapProposal
from app.improvements.yallaplays_improvements import build_yallaplays_improvements


def yallaplays_proposals() -> ImprovementCollection:
    return ImprovementCollection(proposals=build_yallaplays_improvements())


def fionera_proposals() -> ImprovementCollection:
    return ImprovementCollection(proposals=build_fionera_improvements())


def seo_proposal_collection() -> ImprovementCollection:
    proposals = [
        proposal for proposal in build_yallaplays_improvements() + build_fionera_improvements()
        if proposal.improvement_type == "seo"
    ]
    return ImprovementCollection(proposals=proposals)


def ux_proposal_collection() -> ImprovementCollection:
    proposals = [
        proposal for proposal in build_yallaplays_improvements() + build_fionera_improvements()
        if proposal.improvement_type == "ux"
    ]
    return ImprovementCollection(proposals=proposals)


def proposal_roadmap() -> ImprovementRoadmap:
    proposals = build_yallaplays_improvements() + build_fionera_improvements()
    proposals.sort(key=lambda item: (item.priority == "high", item.expected_impact), reverse=True)
    return ImprovementRoadmap(
        roadmap=[
            RoadmapProposal(
                project=proposal.project,
                priority=proposal.priority,
                proposal=proposal.proposal,
                estimated_impact=proposal.expected_impact,
                estimated_effort=proposal.estimated_effort,
                sequence=index + 1,
            )
            for index, proposal in enumerate(proposals[:12])
        ]
    )
