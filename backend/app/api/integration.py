from fastapi import APIRouter, Query

from app.core.projects import PROJECTS
from app.integration.asset_tracker import track_assets
from app.integration.fionera_sync import sync_fionera
from app.integration.models import AssetCollection, IntegrationOverview, IntegrationProjectSummary, SeoGapCollection
from app.integration.repository_reader import read_repository
from app.integration.seo_mapper import analyze_seo_gaps
from app.integration.yallaplays_sync import sync_yallaplays


router = APIRouter(prefix="/integration", tags=["integration"])


@router.get("/projects")
def integration_projects(max_files: int = Query(default=2000, ge=1, le=10000)):
    summaries = []
    for project_id in ("yallaplays", "fionera"):
        project = PROJECTS.get(project_id, {})
        repository, _ = read_repository(project_id, max_files=max_files)
        safe_apply_count = 0
        if project_id == "yallaplays":
            safe_apply_count = len(sync_yallaplays(max_files=max_files).apply_previews)
        elif project_id == "fionera":
            safe_apply_count = len(sync_fionera(max_files=max_files).apply_previews)
        summaries.append(IntegrationProjectSummary(
            project_id=project_id,
            project_name=project.get("name", project_id),
            project_type=project.get("type", ""),
            repository_available=repository.available,
            path=repository.path,
            files_scanned=repository.files_scanned,
            safe_apply_previews=safe_apply_count,
        ))
    return IntegrationOverview(projects=summaries).model_dump()


@router.get("/yallaplays")
def integration_yallaplays(max_files: int = Query(default=2000, ge=1, le=10000)):
    return sync_yallaplays(max_files=max_files).model_dump()


@router.get("/fionera")
def integration_fionera(max_files: int = Query(default=2000, ge=1, le=10000)):
    return sync_fionera(max_files=max_files).model_dump()


@router.get("/seo-gaps")
def integration_seo_gaps(max_files: int = Query(default=2000, ge=1, le=10000)):
    gaps = []
    for project_id in ("yallaplays", "fionera"):
        _, files = read_repository(project_id, max_files=max_files)
        gaps.extend(analyze_seo_gaps(project_id, files))
    return SeoGapCollection(seo_gaps=gaps).model_dump()


@router.get("/assets")
def integration_assets(max_files: int = Query(default=2000, ge=1, le=10000)):
    assets = []
    for project_id in ("yallaplays", "fionera"):
        _, files = read_repository(project_id, max_files=max_files)
        assets.append(track_assets(project_id, files))
    return AssetCollection(assets=assets).model_dump()
