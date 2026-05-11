from app.execution.models import ExecutionPipeline
from app.execution.pipelines import list_pipelines


def scheduler_candidates() -> list[dict]:
    candidates = []
    for pipeline in list_pipelines():
        cadence = "daily" if pipeline.project_id == "fionera" else "weekly"
        candidates.append({
            "pipeline": pipeline.pipeline,
            "project_id": pipeline.project_id,
            "recommended_cadence": cadence,
            "scheduler_mode": "preview_then_validate",
            "requires_manual_apply": True,
        })
    return candidates
