from pydantic import BaseModel, Field


class RepositoryScan(BaseModel):
    project_id: str
    project_name: str = ""
    path: str = ""
    available: bool = False
    files_scanned: int = 0
    directories_scanned: int = 0
    extensions: dict[str, int] = Field(default_factory=dict)
    error: str | None = None


class AssetSummary(BaseModel):
    project_id: str
    images: int = 0
    scripts: int = 0
    stylesheets: int = 0
    data_files: int = 0
    large_assets: list[str] = Field(default_factory=list)


class SeoGap(BaseModel):
    project_id: str
    page: str
    issue: str
    priority: str = "medium"
    recommendation: str = ""


class SafeApplyPreview(BaseModel):
    project_id: str
    title: str
    operation: str = "preview"
    target_files: list[str] = Field(default_factory=list)
    destructive: bool = False
    ready_for_review: bool = True
    notes: list[str] = Field(default_factory=list)


class YallaPlaysIntegration(BaseModel):
    project: str = "yallaplays"
    repository: RepositoryScan
    games_detected: int = 0
    categories_detected: list[str] = Field(default_factory=list)
    missing_categories: list[str] = Field(default_factory=list)
    seo_gaps: list[SeoGap] = Field(default_factory=list)
    metadata_gaps: list[str] = Field(default_factory=list)
    assets: AssetSummary
    apply_previews: list[SafeApplyPreview] = Field(default_factory=list)


class FioneraIntegration(BaseModel):
    project: str = "fionera"
    repository: RepositoryScan
    watchlists_detected: int = 0
    dashboards_detected: int = 0
    missing_features: list[str] = Field(default_factory=list)
    analytics_components: list[str] = Field(default_factory=list)
    ux_gaps: list[str] = Field(default_factory=list)
    assets: AssetSummary
    apply_previews: list[SafeApplyPreview] = Field(default_factory=list)


class IntegrationProjectSummary(BaseModel):
    project_id: str
    project_name: str = ""
    project_type: str = ""
    repository_available: bool = False
    path: str = ""
    files_scanned: int = 0
    safe_apply_previews: int = 0


class IntegrationOverview(BaseModel):
    projects: list[IntegrationProjectSummary] = Field(default_factory=list)


class SeoGapCollection(BaseModel):
    seo_gaps: list[SeoGap] = Field(default_factory=list)


class AssetCollection(BaseModel):
    assets: list[AssetSummary] = Field(default_factory=list)
