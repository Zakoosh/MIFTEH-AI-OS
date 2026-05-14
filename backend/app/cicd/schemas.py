from __future__ import annotations
from pydantic import BaseModel, ConfigDict


class CICDStatusResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    status: str
    active_pipelines: int
    active_deployments: int
    staging_deployments: int
    last_production_deploy: str | None
    safety_mode: bool = True
    auto_deploy_to_production: bool = False


class DeploymentListResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    deployments: list[dict]
    total: int
    by_environment: dict[str, int]
    by_status: dict[str, int]


class StagingStatusResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    active_staging: list[dict]
    total: int
    environments: list[str]


class ReleasesResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    releases: list[dict]
    total: int
    latest_by_project: dict[str, str]


class CICDHealthResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    overall_health: str
    projects: list[dict]
    last_check: str
    deployment_success_rate: float
    avg_pipeline_duration_seconds: float
