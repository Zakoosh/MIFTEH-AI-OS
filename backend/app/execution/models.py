from pydantic import BaseModel, Field
from typing import Optional


PIPELINE_STATUS_PREVIEW = "preview"
PIPELINE_STATUS_VALIDATED = "validated"
PIPELINE_STATUS_FAILED = "failed"


class ExecutionPipeline(BaseModel):
    pipeline: str
    project_id: str
    description: str
    controlled_execution: bool = True
    preview_required: bool = True
    validation_required: bool = True
    deployment_allowed: bool = False
    destructive_operations_allowed: bool = False


class ValidationResult(BaseModel):
    pipeline: str
    validated: bool = False
    ready_for_apply: bool = False
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ExecutionPreview(BaseModel):
    pipeline: str
    project_id: str
    summary: str
    items: list[dict] = Field(default_factory=list)
    validation: Optional[ValidationResult] = None


class ExecutionResult(BaseModel):
    pipeline: str
    project_id: str
    status: str = PIPELINE_STATUS_PREVIEW
    items_generated: int = 0
    signals_collected: int = 0
    insights_generated: int = 0
    validated: bool = False
    ready_for_apply: bool = False
    preview: Optional[ExecutionPreview] = None
    errors: list[str] = Field(default_factory=list)


class ExecutionHistoryEntry(BaseModel):
    execution_id: str
    pipeline: str
    project_id: str
    status: str
    created_at: str
    items_generated: int = 0
    signals_collected: int = 0
    insights_generated: int = 0
    validated: bool = False
    ready_for_apply: bool = False


class ExecutionCollection(BaseModel):
    pipelines: list[ExecutionPipeline] = Field(default_factory=list)


class ExecutionHistoryCollection(BaseModel):
    executions: list[ExecutionHistoryEntry] = Field(default_factory=list)


class ExecutionPreviewCollection(BaseModel):
    previews: list[ExecutionPreview] = Field(default_factory=list)


class ExecutionValidationCollection(BaseModel):
    validations: list[ValidationResult] = Field(default_factory=list)
