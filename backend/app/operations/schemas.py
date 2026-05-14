from __future__ import annotations
from pydantic import BaseModel, ConfigDict
from .models import OutputType, OperationProject


class GenerateRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    project: OperationProject
    output_type: OutputType
    topic: str = ""
    count: int = 1
    use_ai: bool = False
    metadata: dict = {}


class GenerateResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    success: bool
    outputs: list[dict]
    batch_id: str | None = None
    preview_ids: list[str] = []
    message: str
    total_generated: int = 0
    cost_usd: float = 0.0


class OutputsListResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    outputs: list[dict]
    total: int
    by_project: dict[str, int]
    by_type: dict[str, int]
    by_status: dict[str, int]
    pending_apply: int


class PreviewResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    preview: dict
    output: dict
    apply_ready: bool
    estimated_impact: dict


class ApplyOutputRequest(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    output_id: str
    dry_run: bool = True
    notes: str = ""


class ApplyOutputResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    success: bool
    output_id: str
    apply_id: str | None = None
    dry_run: bool
    message: str
    rollback_id: str | None = None


class OperationsStatusResponse(BaseModel):
    model_config = ConfigDict(use_enum_values=True)
    status: str
    yallaplays: dict
    fionera: dict
    total_outputs: int
    pending_apply: int
    last_generation: str | None
    ai_active: bool
