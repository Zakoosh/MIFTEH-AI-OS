from fastapi import APIRouter, Query
from app.engine.execution_engine import execute_single_agent, execute_all_project_agents
from app.engine.memory_engine import list_agent_reports, read_agent_report

router = APIRouter()


@router.get("/run-agent/{project_id}")
def run_project_agent(project_id: str):
    return execute_single_agent(project_id)


@router.get("/run-agents/{project_id}")
def run_project_agents(project_id: str, limit: int = Query(3)):
    return execute_all_project_agents(project_id, limit)


@router.get("/reports")
def get_reports():
    return list_agent_reports()


@router.get("/reports/{filename}")
def get_report(filename: str):
    return read_agent_report(filename)
