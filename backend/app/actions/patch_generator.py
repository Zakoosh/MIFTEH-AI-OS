import difflib
from datetime import datetime
from pathlib import Path

from app.projects.workspace import get_workspace_root


def generate_patch(file_path: str, original_content: str, new_content: str) -> str:
    original_lines = original_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    patch = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )

    return "".join(patch)


def generate_patch_from_action(file_path: str, find: str, replace: str) -> str:
    workspace_root = get_workspace_root()
    absolute_path = (workspace_root / file_path).resolve()

    if not absolute_path.is_file():
        return ""

    try:
        original = absolute_path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""

    if find not in original:
        return ""

    modified = original.replace(find, replace, 1)

    return generate_patch(file_path, original, modified)
