from fastapi import APIRouter, Query
from app.services.agency_indexer import list_agency_agents, load_agency_agent

router = APIRouter()


@router.get("/agency/agents")
def get_agency_agents():
    return list_agency_agents()


@router.get("/agency/agent")
def get_agency_agent(path: str = Query(...)):
    return load_agency_agent(path)
