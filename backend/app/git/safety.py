from pathlib import Path


WORKSPACE_ROOT = Path("/workspace").resolve()
PROTECTED_BRANCHES = {"main", "master"}
BLOCKED_BRANCH_PARTS = {"", ".", ".."}
BLOCKED_BRANCH_TOKENS = ("..", "@{", "\\")
BLOCKED_BRANCH_CHARS = {" ", "~", "^", ":", "?", "*", "["}


class GitSafetyError(ValueError):
    pass


def is_path_within_workspace(path: Path) -> bool:
    resolved = path.resolve()
    return resolved == WORKSPACE_ROOT or WORKSPACE_ROOT in resolved.parents


def resolve_under_workspace(path: Path) -> Path:
    candidate = path if path.is_absolute() else WORKSPACE_ROOT / path
    resolved = candidate.resolve()

    if not is_path_within_workspace(resolved):
        raise GitSafetyError("Git operations are restricted to /workspace")

    return resolved


def ensure_repository_path(path: Path) -> Path:
    resolved = resolve_under_workspace(path)

    if not resolved.exists():
        raise GitSafetyError(f"Repository path does not exist: {resolved}")

    if not resolved.is_dir():
        raise GitSafetyError(f"Repository path is not a directory: {resolved}")

    return resolved


def is_protected_branch(branch_name: str) -> bool:
    return branch_name.strip().lower() in PROTECTED_BRANCHES


def assert_branch_not_protected(branch_name: str, operation: str) -> None:
    if is_protected_branch(branch_name):
        raise GitSafetyError(f"Cannot {operation} on protected branch '{branch_name}'")


def validate_branch_name(branch_name: str) -> str:
    cleaned = branch_name.strip()

    if not cleaned:
        raise GitSafetyError("Branch name is required")

    if is_protected_branch(cleaned):
        raise GitSafetyError(f"Cannot create protected branch '{cleaned}'")

    if cleaned.startswith("-") or cleaned.startswith("/") or cleaned.endswith("/"):
        raise GitSafetyError("Branch name has an invalid boundary character")

    if cleaned.endswith(".lock"):
        raise GitSafetyError("Branch name cannot end with .lock")

    if any(token in cleaned for token in BLOCKED_BRANCH_TOKENS):
        raise GitSafetyError("Branch name contains a blocked token")

    if any(char in cleaned for char in BLOCKED_BRANCH_CHARS):
        raise GitSafetyError("Branch name contains an unsafe character")

    if any(part in BLOCKED_BRANCH_PARTS for part in cleaned.split("/")):
        raise GitSafetyError("Branch name contains an invalid path segment")

    return cleaned


def resolve_repo_file(repo_root: Path, file_path: str) -> str:
    candidate = Path(file_path)
    absolute_path = candidate if candidate.is_absolute() else repo_root / candidate
    resolved = absolute_path.resolve()

    if resolved != repo_root and repo_root not in resolved.parents:
        raise GitSafetyError(f"File path escapes repository: {file_path}")

    return resolved.relative_to(repo_root).as_posix()
