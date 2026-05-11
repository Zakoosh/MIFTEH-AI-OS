from fastapi import APIRouter

from app.execution.batch_runner import run_pipeline
from app.execution.execution_history import load_history
from app.execution.models import (
    ExecutionCollection,
    ExecutionHistoryCollection,
    ExecutionPreviewCollection,
    ExecutionValidationCollection,
)
from app.execution.pipelines import list_pipelines
from app.execution.previews import build_all_previews
from app.execution.scheduling_bridge import scheduler_candidates
from app.execution.schemas import RunPipelineRequest


router = APIRouter(prefix="/execution", tags=["execution"])


@router.get("/pipelines")
def get_execution_pipelines():
    return {
        **ExecutionCollection(pipelines=list_pipelines()).model_dump(),
        "scheduler_candidates": scheduler_candidates(),
    }


@router.post("/run/{pipeline}")
def run_execution_pipeline(pipeline: str, request: RunPipelineRequest):
    return run_pipeline(
        pipeline=pipeline,
        limit=request.limit,
        preview_only=request.preview_only,
    ).model_dump()


@router.get("/history")
def get_execution_history():
    return ExecutionHistoryCollection(executions=load_history()).model_dump()


@router.get("/previews")
def get_execution_previews():
    return ExecutionPreviewCollection(previews=build_all_previews()).model_dump()


@router.get("/validation")
def get_execution_validation():
    validations = [
        preview.validation for preview in build_all_previews()
        if preview.validation is not None
    ]
    return ExecutionValidationCollection(validations=validations).model_dump()
