from datetime import datetime
from pathlib import Path
from typing import Optional

from app.git.diff_manager import generate_diff
from app.git.models import GitPatchFile, GitPatchResult


PATCH_DIR = Path("/workspace/backend/app/memory/reports/git_patches")


def _safe_filename(value: str) -> str:
    cleaned = []
    for char in value:
        if char.isalnum() or char in ("-", "_", "."):
            cleaned.append(char)
        else:
            cleaned.append("-")
    return "".join(cleaned).strip("-") or "unknown"


def _patch_file_from_path(path: Path) -> GitPatchFile:
    stat = path.stat()
    name_parts = path.stem.split("__")
    project_id = name_parts[0] if name_parts else ""

    return GitPatchFile(
        name=path.name,
        path=str(path),
        project_id=project_id,
        created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
        size_bytes=stat.st_size,
    )


def list_patch_files() -> list[GitPatchFile]:
    if not PATCH_DIR.exists():
        return []

    return [
        _patch_file_from_path(path)
        for path in sorted(PATCH_DIR.glob("*.patch"), reverse=True)
        if path.is_file()
    ]


def generate_patch_file(
    project_id: str,
    staged: bool = False,
    base_ref: Optional[str] = None,
) -> GitPatchResult:
    diff_result = generate_diff(
        project_id=project_id,
        staged=staged,
        base_ref=base_ref,
    )

    if not diff_result.success:
        return GitPatchResult(
            success=False,
            project_id=project_id,
            staged=staged,
            base_ref=base_ref,
            patches=list_patch_files(),
            error=diff_result.error,
        )

    if not diff_result.has_changes:
        return GitPatchResult(
            success=False,
            project_id=project_id,
            repository=diff_result.repository,
            staged=staged,
            base_ref=base_ref,
            patches=list_patch_files(),
            error="No changes available for patch generation",
        )

    PATCH_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    branch = diff_result.repository.branch if diff_result.repository else "unknown"
    filename = (
        f"{_safe_filename(project_id)}__"
        f"{_safe_filename(branch)}__"
        f"{timestamp}.patch"
    )
    patch_path = PATCH_DIR / filename
    patch_path.write_text(diff_result.diff, encoding="utf-8")
    patch = _patch_file_from_path(patch_path)

    return GitPatchResult(
        success=True,
        project_id=project_id,
        repository=diff_result.repository,
        staged=staged,
        base_ref=base_ref,
        patch=patch,
        patches=list_patch_files(),
    )
