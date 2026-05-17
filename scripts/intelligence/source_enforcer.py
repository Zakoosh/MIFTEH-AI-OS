"""
Source of Truth Enforcer — prevents fake preview deployments, wrong repo writes,
and static HTML replacements for dynamic frameworks.

HARD RULES enforced here mirror the architecture correction from 2026-05-17.
"""
import re
from pathlib import Path
from typing import Optional
from .registry import load_registry, get_project, get_preview_path

# Paths that are NEVER valid production write targets
_BLOCKED_PATH_PATTERNS = [
    r"frontend/dashboard/previews/",
    r"deploy/yallaplays/",
    r"deploy/fionera/",
    r"/\.next/",
    r"/out/",
    r"/dist/",
    r"/node_modules/",
]

# Frameworks that must NOT receive raw .html replacement files
_DYNAMIC_FRAMEWORKS = {"nextjs", "nuxt", "astro", "vite", "laravel"}

# Static HTML file extensions that are invalid for dynamic frameworks
_STATIC_EXTENSIONS = {".html", ".htm"}


class EnforcementError(Exception):
    """Raised when a write operation violates production source-of-truth rules."""
    pass


def enforce_write(
    write_path: str,
    project_id: str,
    content_type: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """
    Validate a proposed file write against production safety rules.

    Returns a result dict:
      { allowed: bool, reason: str, rule: str, path: str }

    Raises EnforcementError if dry_run=False and write is blocked.
    """
    path = str(write_path).replace("\\", "/")
    result = _check(path, project_id, content_type)

    if not result["allowed"] and not dry_run:
        raise EnforcementError(
            f"[SOURCE ENFORCER] BLOCKED write to '{path}'\n"
            f"  Rule  : {result['rule']}\n"
            f"  Reason: {result['reason']}\n"
            f"  Fix   : Write to the production source at '{result.get('correct_path', '?')}'"
        )
    return result


def get_production_source_path(project_id: str) -> str:
    """Return the correct production source path for a project."""
    p = get_project(project_id)
    repo_root = Path(__file__).parents[2]
    return str(repo_root / p["local_path"])


def is_preview_path(path: str) -> bool:
    return bool(re.search(r"frontend/dashboard/previews/", path))


def is_deploy_artifact(path: str) -> bool:
    return bool(re.search(r"^deploy/", path))


def _check(path: str, project_id: str, content_type: Optional[str]) -> dict:
    # Rule 1: Block writes to preview directories
    if is_preview_path(path):
        return _blocked(
            path, project_id,
            rule="NO_PREVIEW_WRITES",
            reason="frontend/dashboard/previews/ is for dashboard display only, not production",
            correct_path=get_production_source_path(project_id),
        )

    # Rule 2: Block writes to deploy/ artifacts
    if is_deploy_artifact(path):
        return _blocked(
            path, project_id,
            rule="NO_DEPLOY_ARTIFACT_WRITES",
            reason="deploy/ contains CI artifacts generated from source, never the source itself",
            correct_path=get_production_source_path(project_id),
        )

    # Rule 3: Block globally blocked path patterns
    for pattern in _BLOCKED_PATH_PATTERNS:
        if re.search(pattern, path):
            return _blocked(
                path, project_id,
                rule="BLOCKED_PATH_PATTERN",
                reason=f"Path matches blocked pattern: {pattern}",
                correct_path=get_production_source_path(project_id),
            )

    # Rule 4: For dynamic framework projects, block raw static HTML writes
    # to their production source directories
    try:
        p = get_project(project_id)
        framework = _get_project_framework(project_id)
        if framework in _DYNAMIC_FRAMEWORKS:
            ext = Path(path).suffix.lower()
            if ext in _STATIC_EXTENSIONS:
                # Check if the write is inside the production source (not public/)
                production_src = get_production_source_path(project_id)
                if path.startswith(production_src) and "/public/" not in path:
                    return _blocked(
                        path, project_id,
                        rule="NO_STATIC_FOR_DYNAMIC",
                        reason=(
                            f"Project '{project_id}' uses {framework} — "
                            f"raw .html files must not replace framework pages. "
                            f"Use the proper page file format instead."
                        ),
                        correct_path=get_production_source_path(project_id),
                    )
    except (KeyError, Exception):
        pass

    return {"allowed": True, "rule": None, "reason": "OK", "path": path}


def _blocked(path, project_id, rule, reason, correct_path=None) -> dict:
    return {
        "allowed": False,
        "rule": rule,
        "reason": reason,
        "path": path,
        "project_id": project_id,
        "correct_path": correct_path,
    }


def _get_project_framework(project_id: str) -> str:
    """Quick heuristic — detect framework from registry metadata."""
    try:
        p = get_project(project_id)
        local_path = Path(__file__).parents[2] / p["local_path"]
        # Look for framework config files
        if (local_path / "yallaplays" / "next.config.ts").exists():
            return "nextjs"
        if (local_path / "next.config.ts").exists():
            return "nextjs"
        if (local_path / "nuxt.config.ts").exists():
            return "nuxt"
        if (local_path / "astro.config.mjs").exists():
            return "astro"
        return "static"
    except Exception:
        return "static"


def validate_all_writes(writes: list[dict], project_id: str) -> dict:
    """
    Validate a batch of write operations.
    Returns summary with allowed/blocked counts and per-write results.
    """
    results = []
    blocked = 0
    for w in writes:
        r = enforce_write(w["path"], project_id, w.get("content_type"), dry_run=True)
        results.append(r)
        if not r["allowed"]:
            blocked += 1

    return {
        "total": len(writes),
        "allowed": len(writes) - blocked,
        "blocked": blocked,
        "results": results,
    }
