from app.execution.execution_history import record_execution
from app.execution.models import PIPELINE_STATUS_FAILED, PIPELINE_STATUS_VALIDATED, ExecutionResult
from app.execution.pipelines import get_pipeline
from app.execution.previews import build_preview


def run_pipeline(pipeline: str, limit: int = 5, preview_only: bool = True) -> ExecutionResult:
    pipeline_config = get_pipeline(pipeline)
    if pipeline_config is None:
        return ExecutionResult(
            pipeline=pipeline,
            project_id="unknown",
            status=PIPELINE_STATUS_FAILED,
            errors=[f"Unknown pipeline '{pipeline}'"],
        )

    preview = build_preview(pipeline, limit=limit)
    if preview is None:
        return ExecutionResult(
            pipeline=pipeline,
            project_id=pipeline_config.project_id,
            status=PIPELINE_STATUS_FAILED,
            errors=[f"Unable to build preview for '{pipeline}'"],
        )

    validation = preview.validation
    result = ExecutionResult(
        pipeline=pipeline,
        project_id=pipeline_config.project_id,
        status=PIPELINE_STATUS_VALIDATED if validation and validation.validated else PIPELINE_STATUS_FAILED,
        items_generated=len(preview.items),
        signals_collected=sum(1 for item in preview.items if item.get("type") == "market_signal"),
        insights_generated=sum(1 for item in preview.items if item.get("type") == "finance_insight"),
        validated=bool(validation and validation.validated),
        ready_for_apply=bool(validation and validation.ready_for_apply and preview_only),
        preview=preview,
        errors=validation.errors if validation else [],
    )
    record_execution(result)
    return result
