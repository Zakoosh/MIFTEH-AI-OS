from __future__ import annotations
from fastapi import APIRouter, Query
from ..cicd.deployment_engine import DeploymentEngine
from ..cicd.schemas import (
    CICDStatusResponse, DeploymentListResponse, StagingStatusResponse,
    ReleasesResponse, CICDHealthResponse,
)

router = APIRouter(prefix="/cicd", tags=["cicd"])
engine = DeploymentEngine()


@router.get("/status", response_model=CICDStatusResponse)
async def get_status():
    return CICDStatusResponse(**engine.get_system_status())


@router.get("/deployments", response_model=DeploymentListResponse)
async def list_deployments(
    project_id: str | None = Query(None),
    environment: str | None = Query(None),
    status: str | None = Query(None),
):
    deployments = engine.list_deployments(project_id=project_id, environment=environment, status=status)
    by_env: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for d in deployments:
        env = d.get("environment", "unknown")
        st = d.get("status", "unknown")
        by_env[env] = by_env.get(env, 0) + 1
        by_status[st] = by_status.get(st, 0) + 1
    return DeploymentListResponse(
        deployments=deployments,
        total=len(deployments),
        by_environment=by_env,
        by_status=by_status,
    )


@router.get("/staging", response_model=StagingStatusResponse)
async def get_staging(project_id: str | None = Query(None)):
    staging = engine.staging.list_staging(project_id=project_id)
    envs = list({s.get("project_id", "") for s in staging})
    return StagingStatusResponse(active_staging=staging, total=len(staging), environments=envs)


@router.get("/releases", response_model=ReleasesResponse)
async def list_releases(project_id: str | None = Query(None)):
    releases = engine.releases.list_releases(project_id=project_id)
    latest = engine.releases.get_latest_by_project()
    return ReleasesResponse(releases=releases, total=len(releases), latest_by_project=latest)


@router.get("/health", response_model=CICDHealthResponse)
async def get_health():
    all_health = engine.monitor.get_all_health()
    all_deployments = engine.list_deployments()
    success_rate = engine.monitor.compute_success_rate(all_deployments)
    avg_duration = engine.monitor.compute_avg_duration(all_deployments)
    degraded = any(h.get("status") not in ("healthy", "unknown") for h in all_health)
    return CICDHealthResponse(
        overall_health="degraded" if degraded else "healthy",
        projects=all_health,
        last_check=__import__("datetime").datetime.utcnow().isoformat(),
        deployment_success_rate=success_rate,
        avg_pipeline_duration_seconds=avg_duration,
    )
