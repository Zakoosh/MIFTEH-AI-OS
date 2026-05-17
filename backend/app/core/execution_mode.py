"""
execution_mode.py — Execution Mode Router

Controls where changes are written:
  - PREVIEW mode  → frontend/dashboard/previews/<project>/
  - PRODUCTION mode → targets/<project>/  (real git repo)

Every mission, apply action, and file write must route through this module.
It is the single enforcement point separating demo from production.

Safety rules enforced here:
  - Production writes MUST land in targets/<project>/
  - Preview writes MUST land in frontend/dashboard/previews/
  - .env files are always blocked
  - Writing outside a project's own scope is always blocked
"""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import NamedTuple

log = logging.getLogger(__name__)

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
_TARGETS_ROOT = _WORKSPACE_ROOT / "targets"
_PREVIEWS_ROOT = _WORKSPACE_ROOT / "frontend" / "dashboard" / "previews"

# Files/patterns that are never writable regardless of mode
_ABSOLUTE_BLOCKS = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".env.example",
}


class ExecutionMode(str, Enum):
    PREVIEW = "preview"
    PRODUCTION = "production"


class WriteTarget(NamedTuple):
    mode: ExecutionMode
    absolute_path: Path
    project_id: str
    relative_path: str  # relative to the project root (preview or production)


class ExecutionModeError(ValueError):
    pass


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def resolve_write_target(
    project_id: str,
    relative_file_path: str,
    mode: ExecutionMode,
) -> WriteTarget:
    """
    Resolve where a file write should go given project_id, relative path, and mode.

    relative_file_path — path relative to the project root, e.g. "index.html"
    Returns a WriteTarget with the validated absolute path.

    Raises ExecutionModeError if the resulting path is unsafe.
    """
    _assert_not_blocked(relative_file_path)

    if mode == ExecutionMode.PREVIEW:
        root = _get_preview_root(project_id)
    else:
        root = _get_production_root(project_id)

    candidate = (root / relative_file_path).resolve()
    _assert_within_root(candidate, root, project_id, mode)

    return WriteTarget(
        mode=mode,
        absolute_path=candidate,
        project_id=project_id,
        relative_path=relative_file_path,
    )


def resolve_write_path(
    project_id: str,
    relative_file_path: str,
    mode: ExecutionMode,
) -> Path:
    """Convenience wrapper — returns just the absolute Path."""
    return resolve_write_target(project_id, relative_file_path, mode).absolute_path


# ---------------------------------------------------------------------------
# Safety assertions
# ---------------------------------------------------------------------------

def assert_path_in_scope(
    absolute_path: Path | str,
    project_id: str,
    mode: ExecutionMode,
) -> None:
    """
    Raise ExecutionModeError if absolute_path falls outside the allowed scope
    for the given project_id and execution mode.
    """
    path = Path(absolute_path).resolve()
    _assert_not_blocked(path.name)

    if mode == ExecutionMode.PREVIEW:
        root = _get_preview_root(project_id)
    else:
        root = _get_production_root(project_id)

    _assert_within_root(path, root, project_id, mode)


def is_path_in_scope(
    absolute_path: Path | str,
    project_id: str,
    mode: ExecutionMode,
) -> bool:
    """Non-throwing version of assert_path_in_scope."""
    try:
        assert_path_in_scope(absolute_path, project_id, mode)
        return True
    except ExecutionModeError:
        return False


# ---------------------------------------------------------------------------
# Mode detection
# ---------------------------------------------------------------------------

def get_project_mode(project_id: str) -> ExecutionMode:
    """
    Determine the current execution mode for a project.

    Checks execution_mode_config.json in memory, then falls back to PREVIEW
    to be safe by default.
    """
    config_path = _WORKSPACE_ROOT / "memory" / "execution_mode_config.json"
    if config_path.exists():
        import json
        try:
            cfg = json.loads(config_path.read_text())
            # Per-project override
            project_overrides = cfg.get("project_modes", {})
            if project_id in project_overrides:
                raw = project_overrides[project_id]
                return ExecutionMode(raw) if raw in ExecutionMode._value2member_map_ else ExecutionMode.PREVIEW
            # Global mode
            raw_global = cfg.get("default_mode", "preview")
            return ExecutionMode(raw_global) if raw_global in ExecutionMode._value2member_map_ else ExecutionMode.PREVIEW
        except Exception:
            pass
    return ExecutionMode.PREVIEW


def set_project_mode(project_id: str, mode: ExecutionMode) -> None:
    """Persist a per-project mode override to execution_mode_config.json."""
    import json
    config_path = _WORKSPACE_ROOT / "memory" / "execution_mode_config.json"
    try:
        cfg = json.loads(config_path.read_text()) if config_path.exists() else {}
    except Exception:
        cfg = {}
    cfg.setdefault("project_modes", {})[project_id] = mode.value
    config_path.write_text(json.dumps(cfg, indent=2))
    log.info("Set execution mode for %s → %s", project_id, mode.value)


# ---------------------------------------------------------------------------
# Mission context helper
# ---------------------------------------------------------------------------

class MissionContext:
    """
    Attach to every mission so agents know exactly where to write.

    Example:
        ctx = MissionContext.for_project("yallaplays", ExecutionMode.PRODUCTION)
        write_path = ctx.resolve("seo/index.html")
    """

    def __init__(self, project_id: str, mode: ExecutionMode):
        self.project_id = project_id
        self.mode = mode

        from app.core.target_manager import get_target_manager
        mgr = get_target_manager()
        config = mgr.get_project_config(project_id)
        if not config:
            raise ExecutionModeError(f"Unknown project: {project_id}")

        if mode == ExecutionMode.PRODUCTION:
            self.root = mgr.get_target_path(project_id)
        else:
            self.root = mgr.get_preview_path(project_id)

        self.repo_url = config.get("repo", "")
        self.branch = config.get("branch", "main")
        self.allowed_operations = config.get("allowed_operations", [])

    @classmethod
    def for_project(cls, project_id: str, mode: ExecutionMode | None = None) -> "MissionContext":
        if mode is None:
            mode = get_project_mode(project_id)
        return cls(project_id, mode)

    def resolve(self, relative_path: str) -> Path:
        """Resolve a relative path to an absolute write path within this mission's scope."""
        target = resolve_write_path(self.project_id, relative_path, self.mode)
        return target

    def to_dict(self) -> dict:
        return {
            "project_id": self.project_id,
            "mode": self.mode.value,
            "root": str(self.root),
            "repo_url": self.repo_url,
            "branch": self.branch,
            "allowed_operations": self.allowed_operations,
        }


# ---------------------------------------------------------------------------
# Production isolation guards (Mission 6)
# ---------------------------------------------------------------------------

def assert_not_preview_path(absolute_path: Path | str) -> None:
    """
    Hard block: raise ExecutionModeError if path is inside frontend/dashboard/previews/.
    Call this at ANY production write site as a belt-and-suspenders check.
    """
    path = Path(absolute_path).resolve()
    preview_root = _PREVIEWS_ROOT.resolve()
    if path == preview_root or preview_root in path.parents:
        raise ExecutionModeError(
            f"PRODUCTION ISOLATION VIOLATED: attempted write to preview path '{path}'. "
            f"Production writes MUST go to targets/<project>/ only."
        )


def inject_preview_watermark(html: str) -> str:
    """
    Inject a visible 'PREVIEW MODE ONLY' watermark into HTML.
    Call this before writing any preview-mode output.
    """
    watermark = (
        '<div style="position:fixed;top:0;left:0;right:0;z-index:99999;'
        'background:#dc2626;color:#fff;text-align:center;padding:6px 0;'
        'font-family:monospace;font-size:13px;font-weight:bold;letter-spacing:1px;">'
        '⚠ PREVIEW MODE ONLY — NOT PRODUCTION ⚠'
        '</div>'
        '<div style="height:34px"></div>'
    )
    if "<body" in html:
        return html.replace("<body>", "<body>" + watermark, 1).replace(
            '<body dir="rtl">', '<body dir="rtl">' + watermark, 1
        )
    return watermark + html


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_production_root(project_id: str) -> Path:
    from app.core.target_manager import get_target_manager
    return get_target_manager().get_target_path(project_id)


def _get_preview_root(project_id: str) -> Path:
    from app.core.target_manager import get_target_manager
    return get_target_manager().get_preview_path(project_id)


def _assert_not_blocked(filename: str) -> None:
    name = Path(filename).name
    if name in _ABSOLUTE_BLOCKS:
        raise ExecutionModeError(
            f"Writes to '{name}' are permanently blocked (secrets protection)"
        )


def _assert_within_root(
    resolved: Path,
    root: Path,
    project_id: str,
    mode: ExecutionMode,
) -> None:
    if resolved != root and root not in resolved.parents:
        raise ExecutionModeError(
            f"Path escape detected in {mode.value} mode for project '{project_id}'. "
            f"Attempted: {resolved} | Allowed root: {root}"
        )
