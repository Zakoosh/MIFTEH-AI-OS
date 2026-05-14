from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .repository_validation import RepositoryValidation


class FileGeneration:
    def __init__(self):
        self._validator = RepositoryValidation()
        self._memory_dir = Path(__file__).parent.parent / "memory" / "repository_automation" / "generated"
        self._memory_dir.mkdir(parents=True, exist_ok=True)

    def generate_file_patch(self, file_path: str, original_content: str, new_content: str, description: str) -> dict:
        valid, issues = self._validator.validate_file_content(new_content)
        file_ext = Path(file_path).suffix.lstrip(".")
        _, content_issues = self._validator.validate_file_content(new_content, file_ext)

        lines_added = len([l for l in new_content.splitlines() if l.strip()])
        lines_original = len([l for l in original_content.splitlines() if l.strip()])

        return {
            "file_path": file_path,
            "description": description,
            "original_lines": lines_original,
            "new_lines": lines_added,
            "diff_size": abs(lines_added - lines_original),
            "safe": len(content_issues) == 0,
            "warnings": content_issues,
            "generated_at": datetime.utcnow().isoformat(),
            "content": new_content,
        }

    def generate_from_proposal(self, proposal: dict) -> list[dict]:
        patches = []
        for file_entry in proposal.get("files", []):
            file_path = file_entry.get("path", "")
            content = file_entry.get("content", "")
            description = file_entry.get("description", "AI-generated change")
            patch = self.generate_file_patch(
                file_path=file_path,
                original_content=file_entry.get("original_content", ""),
                new_content=content,
                description=description,
            )
            patches.append(patch)
        return patches

    def save_generated_patch(self, patch_id: str, patches: list[dict]) -> Path:
        patch_file = self._memory_dir / f"{patch_id}.json"
        patch_file.write_text(json.dumps(patches, indent=2, default=str))
        return patch_file

    def load_generated_patch(self, patch_id: str) -> list[dict] | None:
        patch_file = self._memory_dir / f"{patch_id}.json"
        if not patch_file.exists():
            return None
        try:
            return json.loads(patch_file.read_text())
        except Exception:
            return None

    def apply_to_preview(self, workspace_path: str, patches: list[dict]) -> tuple[bool, list[str]]:
        workspace = Path(workspace_path)
        if not workspace.exists():
            return False, ["Preview workspace does not exist"]
        errors = []
        for patch in patches:
            file_path = patch.get("file_path", "")
            content = patch.get("content", "")
            if not patch.get("safe", True):
                errors.append(f"Unsafe patch skipped: {file_path}")
                continue
            try:
                target = workspace / file_path.lstrip("/")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            except Exception as e:
                errors.append(f"Failed to write {file_path}: {e}")
        return len(errors) == 0, errors
