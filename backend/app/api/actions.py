from fastapi import APIRouter

from app.actions.models import ActionRequest, RollbackRequest
from app.actions.executor import (
    preview_actions,
    execute_actions,
    rollback_execution,
    get_action_history,
)

router = APIRouter(prefix="/actions", tags=["actions"])


@router.post("/preview")
def preview(request: ActionRequest):
    previews = preview_actions(request.actions)
    return {
        "total": len(previews),
        "previews": previews,
    }


@router.post("/execute")
def execute(request: ActionRequest):
    response = execute_actions(request)
    return response.model_dump()


@router.post("/rollback")
def rollback(request: RollbackRequest):
    return rollback_execution(request.execution_id)


@router.get("/history")
def history():
    entries = get_action_history()
    return {
        "total": len(entries),
        "executions": [e.model_dump() for e in entries],
    }
