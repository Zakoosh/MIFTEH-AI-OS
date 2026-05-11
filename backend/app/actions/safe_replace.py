from pathlib import Path

from app.projects.workspace import get_workspace_root


def replace_in_file(file_path: str, find: str, replace: str) -> dict:
    workspace_root = get_workspace_root()
    absolute_path = (workspace_root / file_path).resolve()

    if not absolute_path.is_file():
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        content = absolute_path.read_text(encoding="utf-8", errors="ignore")
    except Exception as exc:
        return {"success": False, "error": f"Cannot read file: {exc}"}

    if find not in content:
        return {"success": False, "error": "Find string not found in file"}

    new_content = content.replace(find, replace, 1)

    try:
        absolute_path.write_text(new_content, encoding="utf-8")
    except Exception as exc:
        return {"success": False, "error": f"Cannot write file: {exc}"}

    return {"success": True, "path": file_path}
