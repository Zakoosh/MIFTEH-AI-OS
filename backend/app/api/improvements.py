from fastapi import APIRouter

from app.improvements.proposal_engine import (
    fionera_proposals,
    proposal_roadmap,
    seo_proposal_collection,
    ux_proposal_collection,
    yallaplays_proposals,
)


router = APIRouter(prefix="/improvements", tags=["improvements"])


@router.get("/yallaplays")
def get_yallaplays_improvements():
    return yallaplays_proposals().model_dump()


@router.get("/fionera")
def get_fionera_improvements():
    return fionera_proposals().model_dump()


@router.get("/seo")
def get_seo_improvements():
    return seo_proposal_collection().model_dump()


@router.get("/ux")
def get_ux_improvements():
    return ux_proposal_collection().model_dump()


@router.get("/roadmap")
def get_improvements_roadmap():
    return proposal_roadmap().model_dump()
