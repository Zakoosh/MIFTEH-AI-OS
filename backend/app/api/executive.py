from fastapi import APIRouter

from app.executive.engine import (
    executive_metrics,
    executive_overview,
    executive_priorities,
    executive_recommendations,
    executive_resources,
)


router = APIRouter(prefix="/executive", tags=["executive"])


@router.get("/overview")
def get_executive_overview():
    return executive_overview().model_dump()


@router.get("/priorities")
def get_executive_priorities():
    return executive_priorities().model_dump()


@router.get("/resources")
def get_executive_resources():
    return executive_resources().model_dump()


@router.get("/recommendations")
def get_executive_recommendations():
    return executive_recommendations().model_dump()


@router.get("/metrics")
def get_executive_metrics():
    return executive_metrics().model_dump()
