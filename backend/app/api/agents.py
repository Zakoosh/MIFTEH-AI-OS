from fastapi import APIRouter, Query
from app.engine.execution_engine import execute_single_agent, execute_all_project_agents
from app.engine.memory_engine import list_agent_reports, read_agent_report
from app.engine.report_dashboard import reports_dashboard, reports_by_project, reports_by_agent

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


@router.get("/reports/dashboard")
def get_reports_dashboard():
    return reports_dashboard()


@router.get("/reports/summary")
def get_reports_summary():
    return reports_dashboard()


@router.get("/reports/project/{project_id}")
def get_project_reports(project_id: str):
    return reports_by_project(project_id)


@router.get("/reports/agent/{agent_name}")
def get_agent_reports(agent_name: str):
    return reports_by_agent(agent_name)


@router.get("/reports/{filename}")
def get_report(filename: str):
    return read_agent_report(filename)
