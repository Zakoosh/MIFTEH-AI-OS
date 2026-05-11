from pathlib import Path

from app.actions.models import FileAction, ActionPreview, ValidationIssue
from app.actions.schemas import (
    SUPPORTED_ACTION_TYPES,
    MAX_FILE_SIZE,
    is_path_blocked,
    is_within_workspace,
)
from app.projects.workspace import get_workspace_root


def validate_action(action: FileAction, action_index: int) -> ActionPreview:
    issues: list[str] = []
    workspace_root = get_workspace_root()

    if action.type not in SUPPORTED_ACTION_TYPES:
        issues.append(f"Unsupported action type: {action.type}")

    if not action.path:
        issues.append("Path is empty")
        return ActionPreview(
            action_index=action_index, path=action.path,
            valid=False, issues=issues,
        )

    if not action.find:
        issues.append("Find string is empty")

    absolute_path = (workspace_root / action.path).resolve()

    if not is_within_workspace(absolute_path, workspace_root):
        issues.append("Path escapes workspace boundary")
        return ActionPreview(
            action_index=action_index, path=action.path,
            valid=False, issues=issues,
        )

    blocked, reason = is_path_blocked(action.path)
    if blocked:
        issues.append(reason)

    if not absolute_path.is_file():
        issues.append(f"File not found: {action.path}")
        return ActionPreview(
            action_index=action_index, path=action.path,
            valid=False, issues=issues,
        )

    try:
        file_size = absolute_path.stat().st_size
        if file_size > MAX_FILE_SIZE:
            issues.append(f"File too large: {file_size} bytes (max {MAX_FILE_SIZE})")
    except OSError as exc:
        issues.append(f"Cannot stat file: {exc}")

    find_found = False
    if action.find and absolute_path.is_file() and not issues:
        try:
            content = absolute_path.read_text(encoding="utf-8", errors="ignore")
            find_found = action.find in content
            if not find_found:
                issues.append("Find string not found in file")
        except Exception as exc:
            issues.append(f"Cannot read file: {exc}")

    valid = len(issues) == 0

    return ActionPreview(
        action_index=action_index,
        path=action.path,
        valid=valid,
        issues=issues,
        find_found=find_found,
    )


def validate_actions(actions: list[FileAction]) -> list[ActionPreview]:
    return [validate_action(action, i) for i, action in enumerate(actions)]
