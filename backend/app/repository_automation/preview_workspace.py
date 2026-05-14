from __future__ import annotations
from datetime import datetime, timedelta
from pathlib import Path
import json
import shutil
from .models import PreviewWorkspace, PreviewStatus


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "repository_automation"
WORKSPACES_DIR = MEMORY_DIR / "workspaces"


class PreviewWorkspaceManager:
    DEFAULT_TTL_HOURS = 24

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)
        self._index_path = MEMORY_DIR / "workspaces.json"

    def _load(self) -> list[dict]:
        if not self._index_path.exists():
            return []
        try:
            return json.loads(self._index_path.read_text())
        except Exception:
            return []

    def _save(self, data: list[dict]) -> None:
        self._index_path.write_text(json.dumps(data, indent=2, default=str))

    def create_workspace(self, project_id: str, source_path: str | None = None, change_ids: list[str] | None = None) -> PreviewWorkspace:
        workspace = PreviewWorkspace(
            project_id=project_id,
            workspace_path="",
            change_ids=change_ids or [],
            status=PreviewStatus.creating,
            expires_at=datetime.utcnow() + timedelta(hours=self.DEFAULT_TTL_HOURS),
        )
        ws_dir = WORKSPACES_DIR / workspace.id
        ws_dir.mkdir(parents=True, exist_ok=True)

        if source_path and Path(source_path).exists():
            try:
                shutil.copytree(source_path, ws_dir / "source", dirs_exist_ok=True)
            except Exception:
                pass

        workspace.workspace_path = str(ws_dir)
        workspace.status = PreviewStatus.ready

        workspaces = self._load()
        workspaces.append(workspace.model_dump())
        self._save(workspaces)
        return workspace

    def get_workspace(self, workspace_id: str) -> dict | None:
        for ws in self._load():
            if ws["id"] == workspace_id:
                return ws
        return None

    def list_workspaces(self, project_id: str | None = None, active_only: bool = True) -> list[dict]:
        workspaces = self._load()
        if project_id:
            workspaces = [w for w in workspaces if w.get("project_id") == project_id]
        if active_only:
            workspaces = [w for w in workspaces if w.get("status") == "ready"]
        return workspaces

    def generate_preview_report(self, workspace_id: str, patches: list[dict]) -> str:
        lines = [
            f"# Preview Report — Workspace {workspace_id[:8]}",
            f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            f"## Changes ({len(patches)} patches)",
        ]
        for p in patches:
            safe_icon = "✓" if p.get("safe") else "⚠"
            lines.append(f"- {safe_icon} `{p.get('file_path', 'unknown')}` — {p.get('description', '')}")
            if p.get("warnings"):
                for w in p["warnings"]:
                    lines.append(f"  - ⚠ {w}")
        lines += ["", "## Safety Status", "- No direct production writes", "- Preview-only workspace", "- Requires manual approval to apply"]
        return "\n".join(lines)

    def destroy_workspace(self, workspace_id: str) -> bool:
        workspaces = self._load()
        for ws in workspaces:
            if ws["id"] == workspace_id:
                ws_path = Path(ws.get("workspace_path", ""))
                if ws_path.exists() and WORKSPACES_DIR in ws_path.parents:
                    try:
                        shutil.rmtree(ws_path)
                    except Exception:
                        pass
                ws["status"] = "destroyed"
                ws["destroyed_at"] = datetime.utcnow().isoformat()
                self._save(workspaces)
                return True
        return False

    def expire_old_workspaces(self) -> int:
        workspaces = self._load()
        now = datetime.utcnow()
        count = 0
        for ws in workspaces:
            if ws.get("status") != "ready":
                continue
            expires = ws.get("expires_at")
            if expires:
                try:
                    exp_dt = datetime.fromisoformat(expires.replace("Z", ""))
                    if now > exp_dt:
                        ws["status"] = "expired"
                        count += 1
                except Exception:
                    pass
        if count:
            self._save(workspaces)
        return count
