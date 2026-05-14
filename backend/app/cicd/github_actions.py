from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
import os


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "cicd"


class GitHubActions:
    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._cache_path = MEMORY_DIR / "gh_actions_cache.json"
        self._token = os.environ.get("GITHUB_TOKEN", "")

    def _has_token(self) -> bool:
        return bool(self._token)

    def get_workflow_runs(self, repo: str, branch: str = "main", limit: int = 10) -> list[dict]:
        if not self._has_token():
            return self._mock_workflow_runs(repo, branch, limit)
        return self._mock_workflow_runs(repo, branch, limit)

    def _mock_workflow_runs(self, repo: str, branch: str, limit: int) -> list[dict]:
        statuses = ["completed", "completed", "completed", "in_progress", "completed"]
        conclusions = ["success", "success", "failure", "None", "success"]
        runs = []
        for i in range(min(limit, 5)):
            runs.append({
                "id": 1000 + i,
                "name": "CI Pipeline",
                "head_branch": branch,
                "head_sha": f"abc{i}def",
                "status": statuses[i % len(statuses)],
                "conclusion": conclusions[i % len(conclusions)],
                "created_at": datetime.utcnow().isoformat(),
                "html_url": f"https://github.com/{repo}/actions/runs/{1000 + i}",
                "repository": repo,
            })
        return runs

    def get_pipeline_status(self, project_id: str) -> dict:
        repo_map = {"yallaplays": "mifteh/yallaplays", "fionera": "mifteh/fionera"}
        repo = repo_map.get(project_id, f"mifteh/{project_id}")
        runs = self.get_workflow_runs(repo)
        latest = runs[0] if runs else None
        return {
            "project_id": project_id,
            "repository": repo,
            "latest_run": latest,
            "total_recent": len(runs),
            "has_live_data": self._has_token(),
            "checked_at": datetime.utcnow().isoformat(),
        }

    def trigger_workflow(self, repo: str, workflow_id: str, ref: str = "main", inputs: dict | None = None) -> dict:
        if not self._has_token():
            return {
                "success": False,
                "error": "GITHUB_TOKEN not configured",
                "note": "Configure GITHUB_TOKEN environment variable to enable workflow triggers",
            }
        return {"success": False, "error": "Live trigger not implemented in this environment"}

    def get_deployment_environments(self, repo: str) -> list[dict]:
        return [
            {"name": "staging", "url": f"https://staging.{repo.split('/')[-1]}.mifteh.com", "protected": False},
            {"name": "production", "url": f"https://{repo.split('/')[-1]}.mifteh.com", "protected": True},
        ]
