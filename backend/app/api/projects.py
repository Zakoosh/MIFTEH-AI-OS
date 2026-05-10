from fastapi import APIRouter, Query
from app.services.project_scanner import scan_project, read_project_file

router = APIRouter()


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    return scan_project(project_id)


@router.get("/projects/{project_id}/file")
def get_project_file(project_id: str, path: str = Query(...)):
    return read_project_file(project_id, path)
