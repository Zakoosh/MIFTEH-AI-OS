import json
import re
from datetime import datetime
from pathlib import Path

from app.actions.models import (
    FileAction,
    ActionRequest,
    ActionResult,
    ExecutionResponse,
    ActionHistoryEntry,
    BackupRecord,
)
from app.actions.validator import validate_action
from app.actions.preview import generate_diff
from app.actions.safe_replace import replace_in_file
from app.actions.patch_generator import generate_patch_from_action
from app.actions.rollback import create_backup, restore_execution

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
ACTIONS_HISTORY_DIR = _BASE_DIR / "app" / "memory" / "actions"


def _safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]", "-", value)


def _generate_execution_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return f"action_{timestamp}"


def _save_execution(execution_id: str, response: ExecutionResponse) -> None:
    ACTIONS_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    file_path = ACTIONS_HISTORY_DIR / f"{execution_id}.json"
    file_path.write_text(
        json.dumps(response.model_dump(), indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )


def _load_execution(execution_id: str) -> ExecutionResponse | None:
    file_path = ACTIONS_HISTORY_DIR / f"{execution_id}.json"
    if not file_path.is_file():
        return None
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
        return ExecutionResponse(**data)
    except Exception:
        return None


def preview_actions(actions: list[FileAction]) -> list[dict]:
    previews: list[dict] = []

    for i, action in enumerate(actions):
        validation = validate_action(action, i)
        diff = ""
        if validation.valid:
            diff = generate_diff(action.path, action.find, action.replace)

        previews.append({
            "action_index": i,
            "path": action.path,
            "type": action.type,
            "valid": validation.valid,
            "issues": validation.issues,
            "find_found": validation.find_found,
            "diff": diff,
        })

    return previews


def execute_actions(request: ActionRequest) -> ExecutionResponse:
    execution_id = _generate_execution_id()
    started_at = datetime.now().isoformat()
    results: list[ActionResult] = []

    for i, action in enumerate(request.actions):
        validation = validate_action(action, i)

        if not validation.valid:
            results.append(ActionResult(
                action_index=i,
                path=action.path,
                status="skipped",
                applied=False,
                error="; ".join(validation.issues),
            ))
            continue

        if request.dry_run:
            diff = generate_diff(action.path, action.find, action.replace)
            results.append(ActionResult(
                action_index=i,
                path=action.path,
                status="preview",
                applied=False,
                diff=diff,
            ))
            continue

        patch = generate_patch_from_action(action.path, action.find, action.replace)
        backup = create_backup(action.path, execution_id)
        replace_result = replace_in_file(action.path, action.find, action.replace)

        if replace_result["success"]:
            results.append(ActionResult(
                action_index=i,
                path=action.path,
                status="applied",
                applied=True,
                diff=generate_diff(action.path, action.find, action.replace),
                patch=patch,
                backup=backup,
            ))
        else:
            results.append(ActionResult(
                action_index=i,
                path=action.path,
                status="failed",
                applied=False,
                backup=backup,
                error=replace_result.get("error", "Unknown error"),
            ))

    applied = sum(1 for r in results if r.applied)
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status in ("skipped", "preview"))

    status = "completed"
    if request.dry_run:
        status = "preview"
    elif failed > 0:
        status = "completed_with_failures"

    response = ExecutionResponse(
        execution_id=execution_id,
        status=status,
        total_actions=len(results),
        applied_count=applied,
        failed_count=failed,
        skipped_count=skipped,
        results=results,
        created_at=started_at,
    )

    _save_execution(execution_id, response)

    return response


def rollback_execution(execution_id: str) -> dict:
    execution = _load_execution(execution_id)

    if execution is None:
        return {"error": f"Execution '{execution_id}' not found"}

    backups: list[BackupRecord] = []
    for result in execution.results:
        if result.backup and result.backup.backup_path:
            backups.append(result.backup)

    if not backups:
        return {"error": "No backups found for this execution"}

    return restore_execution(execution_id, backups)


def get_action_history() -> list[ActionHistoryEntry]:
    ACTIONS_HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    entries: list[ActionHistoryEntry] = []

    for file_path in ACTIONS_HISTORY_DIR.glob("*.json"):
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            entries.append(ActionHistoryEntry(
                execution_id=data.get("execution_id", file_path.stem),
                total_actions=data.get("total_actions", 0),
                applied_count=data.get("applied_count", 0),
                failed_count=data.get("failed_count", 0),
                status=data.get("status", "unknown"),
                created_at=data.get("created_at", ""),
            ))
        except Exception:
            continue

    entries.sort(key=lambda e: e.created_at or "", reverse=True)
    return entries
