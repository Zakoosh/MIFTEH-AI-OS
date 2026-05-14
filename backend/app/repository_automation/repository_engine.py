from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import RepositoryProject, RepositoryChange, ChangeType, ChangeStatus
from .change_tracker import ChangeTracker
from .branch_manager import BranchManager
from .pr_generator import PRGenerator
from .file_generation import FileGeneration
from .preview_workspace import PreviewWorkspaceManager
from .repository_validation import RepositoryValidation


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "repository_automation"

KNOWN_PROJECTS = [
    RepositoryProject(
        id="yallaplays",
        name="YallaPlays",
        repo_url="https://github.com/mifteh/yallaplays",
        local_path="/repos/yallaplays",
        default_branch="main",
        description="YallaPlays gaming platform",
    ),
    RepositoryProject(
        id="fionera",
        name="Fionera",
        repo_url="https://github.com/mifteh/fionera",
        local_path="/repos/fionera",
        default_branch="main",
        description="Fionera platform",
    ),
]


class RepositoryEngine:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._projects_path = MEMORY_DIR / "projects.json"
        self.tracker = ChangeTracker()
        self.branches = BranchManager()
        self.pr_gen = PRGenerator()
        self.file_gen = FileGeneration()
        self.workspace_mgr = PreviewWorkspaceManager()
        self.validator = RepositoryValidation()
        self._ensure_projects()

    def _ensure_projects(self) -> None:
        if not self._projects_path.exists():
            data = [p.model_dump() for p in KNOWN_PROJECTS]
            self._projects_path.write_text(json.dumps(data, indent=2, default=str))

    def list_projects(self) -> list[dict]:
        try:
            return json.loads(self._projects_path.read_text())
        except Exception:
            return [p.model_dump() for p in KNOWN_PROJECTS]

    def get_project(self, project_id: str) -> dict | None:
        for p in self.list_projects():
            if p["id"] == project_id or p["name"].lower() == project_id.lower():
                return p
        return None

    def register_change(self, project_id: str, change_type: ChangeType, files: list[str], description: str) -> RepositoryChange:
        valid, issues = self.validator.validate_change_set([{"files_affected": files, "description": description, "change_type": change_type}])
        change = RepositoryChange(
            project_id=project_id,
            change_type=change_type,
            files_affected=files,
            description=description,
            status=ChangeStatus.draft,
            metadata={"validation_passed": valid, "validation_issues": issues},
        )
        return self.tracker.record_change(change)

    def generate_pr_workflow(self, project_id: str, change_ids: list[str], title: str, description: str) -> dict:
        project = self.get_project(project_id)
        if not project:
            return {"success": False, "error": f"Project not found: {project_id}"}

        changes = [self.tracker.get_change(cid) for cid in change_ids if self.tracker.get_change(cid)]
        if not changes:
            return {"success": False, "error": "No valid changes found"}

        valid, issues = self.validator.validate_pr_metadata(title, description)
        if not valid:
            return {"success": False, "error": "; ".join(issues)}

        branch_name = self.branches.suggest_branch_name(project["name"], "feature", title)
        branch_record, branch_msg = self.branches.create_branch_record(
            project_id=project_id,
            branch_name=branch_name,
            base_branch=project.get("default_branch", "main"),
            purpose=title,
        )
        if not branch_record:
            return {"success": False, "error": f"Branch creation failed: {branch_msg}"}

        workspace = self.workspace_mgr.create_workspace(project_id=project_id, change_ids=change_ids)

        pr_draft, pr_msg = self.pr_gen.generate_pr_draft(
            project_id=project_id,
            branch_id=branch_record.id,
            title=title,
            description=description,
            changes=changes,
        )
        if not pr_draft:
            return {"success": False, "error": f"PR generation failed: {pr_msg}"}

        markdown_body = self.pr_gen.generate_markdown_body(pr_draft)
        preview_report = self.workspace_mgr.generate_preview_report(workspace.id, [])

        for cid in change_ids:
            self.tracker.update_change_status(cid, ChangeStatus.preview, {"pr_id": pr_draft.id, "workspace_id": workspace.id})

        return {
            "success": True,
            "pr_draft": pr_draft.model_dump(),
            "branch": branch_record.model_dump(),
            "preview_workspace": workspace.model_dump(),
            "markdown_body": markdown_body,
            "preview_report": preview_report,
            "message": "PR workflow generated — requires manual review before merge",
        }

    def get_status(self) -> dict:
        projects = self.list_projects()
        changes = self.tracker.get_changes()
        previews = self.workspace_mgr.list_workspaces()
        prs = self.pr_gen.list_prs()
        return {
            "status": "operational",
            "projects_tracked": len(projects),
            "pending_changes": len([c for c in changes if c.get("status") == "draft"]),
            "active_previews": len(previews),
            "open_prs": len([p for p in prs if p.get("status") in ("draft", "ready")]),
            "last_activity": datetime.utcnow().isoformat(),
            "safety_mode": True,
        }
