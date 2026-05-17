"""Validate every entry in targets/registry.json."""
import json
import subprocess
import os
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class RegistryEntryHealth:
    project_id: str
    local_path_exists: bool
    is_git_repo: bool
    remote_url: str
    branch_exists: bool
    pages_configured: bool
    adsense_configured: bool
    issues: List[str] = field(default_factory=list)
    healthy: bool = False


def validate_registry(registry_path: str) -> List[RegistryEntryHealth]:
    """Validate all entries in registry.json."""
    with open(registry_path) as f:
        registry = json.load(f)

    results = []

    for project in registry.get("projects", []):
        pid = project.get("id", "unknown")
        local_path = project.get("local_path", "")
        issues = []

        # Resolve path relative to registry file location
        base_dir = os.path.dirname(registry_path)
        if local_path.startswith("./"):
            abs_path = os.path.join(base_dir, local_path[2:])
        else:
            abs_path = local_path

        local_exists = os.path.isdir(abs_path)
        if not local_exists:
            issues.append(f"local_path not found: {abs_path}")

        is_git = os.path.isdir(os.path.join(abs_path, ".git")) if local_exists else False
        if local_exists and not is_git:
            issues.append("directory exists but is not a git repo")

        remote_url = ""
        branch_exists = False
        if is_git:
            r = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=abs_path, capture_output=True, text=True,
            )
            remote_url = r.stdout.strip() if r.returncode == 0 else ""
            if not remote_url:
                issues.append("no git remote 'origin'")

            branch = project.get("branch", "main")
            b = subprocess.run(
                ["git", "branch", "--list", branch],
                cwd=abs_path, capture_output=True, text=True,
            )
            branch_exists = bool(b.stdout.strip())
            if not branch_exists:
                # Also check remote branches
                rb = subprocess.run(
                    ["git", "branch", "-r", "--list", f"origin/{branch}"],
                    cwd=abs_path, capture_output=True, text=True,
                )
                branch_exists = bool(rb.stdout.strip())
            if not branch_exists:
                issues.append(f"branch '{branch}' not found locally or remotely")

        pages_configured = bool(project.get("pages_url") or project.get("domain"))
        if not pages_configured:
            issues.append("no pages_url or domain configured")

        adsense = project.get("adsense", {})
        adsense_configured = bool(adsense.get("publisher_id"))
        if not adsense_configured:
            issues.append("no adsense.publisher_id")

        health = RegistryEntryHealth(
            project_id=pid,
            local_path_exists=local_exists,
            is_git_repo=is_git,
            remote_url=remote_url,
            branch_exists=branch_exists,
            pages_configured=pages_configured,
            adsense_configured=adsense_configured,
            issues=issues,
            healthy=len(issues) == 0,
        )
        results.append(health)

    return results
