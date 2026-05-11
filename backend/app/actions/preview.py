import difflib
from pathlib import Path

from app.projects.workspace import get_workspace_root


def generate_diff(file_path: str, find: str, replace: str) -> str:
    workspace_root = get_workspace_root()
    absolute_path = (workspace_root / file_path).resolve()

    if not absolute_path.is_file():
        return f"--- {file_path}\n+++ {file_path}\n@@ File not found @@\n"

    try:
        original = absolute_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return f"--- {file_path}\n+++ {file_path}\n@@ Cannot read: {exc} @@\n"

    if find not in original:
        return f"--- {file_path}\n+++ {file_path}\n@@ Find string not present @@\n"

    modified = original.replace(find, replace, 1)

    original_lines = original.splitlines(keepends=True)
    modified_lines = modified.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        modified_lines,
        fromfile=f"a/{file_path}",
        tofile=f"b/{file_path}",
        lineterm="",
    )

    return "".join(diff)


def generate_preview_text(file_path: str, find: str, replace: str) -> str:
    lines = [
        f"File: {file_path}",
        f"Action: replace_in_file",
        f"Find ({len(find)} chars):",
        f"  {find[:200]}{'...' if len(find) > 200 else ''}",
        f"Replace ({len(replace)} chars):",
        f"  {replace[:200]}{'...' if len(replace) > 200 else ''}",
        "",
        "Diff:",
        generate_diff(file_path, find, replace),
    ]
    return "\n".join(lines)
