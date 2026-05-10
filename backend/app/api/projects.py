from fastapi import APIRouter, Query
from app.services.project_scanner import scan_project, read_project_file, search_project

router = APIRouter()


@router.get("/projects/{project_id}")
def get_project(project_id: str):
    return scan_project(project_id)


@router.get("/projects/{project_id}/file")
def get_project_file(project_id: str, path: str = Query(...)):
    return read_project_file(project_id, path)


@router.get("/projects/{project_id}/search")
def search_in_project(project_id: str, q: str = Query(...)):
    return search_project(project_id, q)
