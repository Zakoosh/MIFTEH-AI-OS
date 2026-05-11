from pathlib import Path

SUPPORTED_ACTION_TYPES = {"replace_in_file"}

BLOCKED_DIRECTORIES = {
    ".git",
    "node_modules",
    "venv",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".cache",
}

BLOCKED_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
}

BLOCKED_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".so",
    ".dll",
    ".exe",
    ".bin",
}

MAX_FILE_SIZE = 1_000_000  # 1 MB

BACKUP_DIR_NAME = ".mifteh_backups"


def is_path_blocked(relative_path: str) -> tuple[bool, str]:
    path = Path(relative_path)

    for part in path.parts:
        if part in BLOCKED_DIRECTORIES:
            return True, f"Path contains blocked directory: {part}"

    if path.name in BLOCKED_FILENAMES:
        return True, f"File is blocked: {path.name}"

    if path.suffix in BLOCKED_EXTENSIONS:
        return True, f"Extension is blocked: {path.suffix}"

    return False, ""


def is_within_workspace(absolute_path: Path, workspace_root: Path) -> bool:
    try:
        absolute_path.resolve().relative_to(workspace_root.resolve())
        return True
    except ValueError:
        return False
