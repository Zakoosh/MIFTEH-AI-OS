from __future__ import annotations
from pathlib import Path
import json
import re


class RepositoryValidation:
    UNSAFE_PATTERNS = [
        r"rm\s+-rf",
        r"DROP\s+TABLE",
        r"DELETE\s+FROM\s+\w+\s*;?\s*$",
        r"os\.system\(",
        r"subprocess\.call\(['\"]rm",
        r"shutil\.rmtree\(",
    ]

    def validate_branch_name(self, name: str) -> tuple[bool, str]:
        if not name:
            return False, "Branch name cannot be empty"
        if not re.match(r"^[a-zA-Z0-9/_\-\.]+$", name):
            return False, f"Invalid branch name: {name}. Use alphanumeric, /, -, _, . only"
        protected = ["main", "master", "production", "prod", "release"]
        if name.lower() in protected:
            return False, f"Cannot use protected branch name: {name}"
        if len(name) > 100:
            return False, "Branch name too long (max 100 chars)"
        return True, "valid"

    def validate_file_path(self, file_path: str, project_root: str | None = None) -> tuple[bool, str]:
        p = Path(file_path)
        if p.is_absolute() and project_root:
            root = Path(project_root)
            try:
                p.relative_to(root)
            except ValueError:
                return False, f"Path {file_path} escapes project root"
        if ".." in p.parts:
            return False, "Path traversal detected"
        return True, "valid"

    def validate_file_content(self, content: str, file_type: str = "unknown") -> tuple[bool, list[str]]:
        warnings = []
        for pattern in self.UNSAFE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append(f"Potentially unsafe pattern detected: {pattern}")
        if file_type in ("py", "python") and len(content) > 500_000:
            warnings.append("File is very large (>500KB)")
        return len(warnings) == 0, warnings

    def validate_change_set(self, changes: list[dict]) -> tuple[bool, list[str]]:
        issues = []
        if len(changes) > 50:
            issues.append("Too many changes in one batch (max 50)")
        seen_files: set[str] = set()
        for change in changes:
            files = change.get("files_affected", [])
            for f in files:
                if f in seen_files:
                    issues.append(f"Duplicate file in change set: {f}")
                seen_files.add(f)
        return len(issues) == 0, issues

    def validate_pr_metadata(self, title: str, description: str) -> tuple[bool, list[str]]:
        issues = []
        if not title or len(title.strip()) < 5:
            issues.append("PR title too short (min 5 characters)")
        if len(title) > 200:
            issues.append("PR title too long (max 200 characters)")
        if not description or len(description.strip()) < 20:
            issues.append("PR description too short (min 20 characters)")
        return len(issues) == 0, issues
