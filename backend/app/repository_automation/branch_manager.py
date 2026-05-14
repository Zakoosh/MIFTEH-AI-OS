from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
import subprocess
from .models import BranchRecord, BranchStatus
from .repository_validation import RepositoryValidation


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "repository_automation"


class BranchManager:
    def __init__(self):
        self._branches_path = MEMORY_DIR / "branches.json"
        self._validator = RepositoryValidation()
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def _load(self) -> list[dict]:
        if not self._branches_path.exists():
            return []
        try:
            return json.loads(self._branches_path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._branches_path.write_text(json.dumps(data, indent=2, default=str))

    def create_branch_record(self, project_id: str, branch_name: str, base_branch: str, purpose: str) -> tuple[BranchRecord | None, str]:
        valid, msg = self._validator.validate_branch_name(branch_name)
        if not valid:
            return None, msg
        branches = self._load()
        for b in branches:
            if b["project_id"] == project_id and b["branch_name"] == branch_name and b["status"] == "active":
                return None, f"Branch {branch_name} already exists for project {project_id}"
        record = BranchRecord(
            project_id=project_id,
            branch_name=branch_name,
            base_branch=base_branch,
            purpose=purpose,
        )
        branches.append(record.model_dump())
        self._save(branches)
        return record, "created"

    def list_branches(self, project_id: str | None = None, status: str | None = None) -> list[dict]:
        branches = self._load()
        if project_id:
            branches = [b for b in branches if b.get("project_id") == project_id]
        if status:
            branches = [b for b in branches if b.get("status") == status]
        return branches

    def get_branch(self, branch_id: str) -> dict | None:
        for b in self._load():
            if b["id"] == branch_id:
                return b
        return None

    def update_branch_status(self, branch_id: str, status: BranchStatus) -> bool:
        branches = self._load()
        for b in branches:
            if b["id"] == branch_id:
                b["status"] = status.value if hasattr(status, "value") else status
                b["updated_at"] = datetime.utcnow().isoformat()
                self._save(branches)
                return True
        return False

    def suggest_branch_name(self, project_name: str, change_type: str, description: str) -> str:
        slug = description.lower().replace(" ", "-")[:40]
        slug = "".join(c for c in slug if c.isalnum() or c == "-")
        return f"ai/{change_type}/{slug}"

    def execute_git_create_branch(self, repo_path: str, branch_name: str, base_branch: str = "main") -> tuple[bool, str]:
        valid, msg = self._validator.validate_branch_name(branch_name)
        if not valid:
            return False, msg
        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "checkout", "-b", branch_name, f"origin/{base_branch}"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                return True, f"Branch {branch_name} created"
            return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Git operation timed out"
        except FileNotFoundError:
            return False, "Git not found or repo path invalid"
        except Exception as e:
            return False, str(e)
