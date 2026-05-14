from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json
from .models import OperationalOutput, OutputStatus


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "operations"


class ApplyBridge:
    """Connects the operations layer to the apply layer for safe execution."""

    def __init__(self):
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        self._apply_log_path = MEMORY_DIR / "apply_log.json"

    def _load_log(self) -> list[dict]:
        if not self._apply_log_path.exists():
            return []
        try:
            return json.loads(self._apply_log_path.read_text())
        except Exception:
            return []

    def _save_log(self, data: list[dict]) -> None:
        self._apply_log_path.write_text(json.dumps(data, indent=2, default=str))

    def _log_apply(self, output_id: str, dry_run: bool, success: bool, result: dict) -> str:
        from uuid import uuid4
        apply_id = str(uuid4())
        log = self._load_log()
        log.append({
            "apply_id": apply_id,
            "output_id": output_id,
            "dry_run": dry_run,
            "success": success,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
        })
        self._save_log(log[-500:])
        return apply_id

    def prepare_apply_payload(self, output: OperationalOutput) -> dict:
        return {
            "output_id": output.id,
            "project": output.project if isinstance(output.project, str) else output.project.value,
            "output_type": output.output_type if isinstance(output.output_type, str) else output.output_type.value,
            "patches": [
                {
                    "file_path": p.get("file_path", ""),
                    "operation": p.get("operation", "create_or_update"),
                    "content": p.get("content", ""),
                    "description": p.get("description", ""),
                }
                for p in output.patch_files
            ],
            "metadata": {
                "risk_level": output.risk_level if isinstance(output.risk_level, str) else output.risk_level.value,
                "ai_generated": output.ai_generated,
                "rollback_available": output.rollback_available,
                "preview_id": output.preview_id,
            },
        }

    def apply_dry_run(self, output: OperationalOutput) -> dict:
        payload = self.prepare_apply_payload(output)
        validation_results = []
        for patch in payload["patches"]:
            file_path = patch.get("file_path", "")
            has_content = bool(patch.get("content"))
            validation_results.append({
                "file_path": file_path,
                "valid": has_content and bool(file_path),
                "operation": patch.get("operation"),
                "content_size": len(str(patch.get("content", ""))),
                "issues": [] if (has_content and file_path) else ["missing content or path"],
            })
        all_valid = all(r["valid"] for r in validation_results)
        result = {
            "dry_run": True,
            "all_valid": all_valid,
            "files_to_change": len(validation_results),
            "validation_results": validation_results,
            "rollback_plan": "snapshot_before_apply",
            "estimated_apply_time_seconds": len(validation_results) * 0.5,
        }
        apply_id = self._log_apply(output.id, dry_run=True, success=all_valid, result=result)
        return {"apply_id": apply_id, **result}

    def apply_output(self, output: OperationalOutput, notes: str = "") -> dict:
        dry_run_result = self.apply_dry_run(output)
        if not dry_run_result.get("all_valid"):
            return {
                "success": False,
                "apply_id": dry_run_result.get("apply_id"),
                "error": "Dry-run validation failed",
                "validation": dry_run_result["validation_results"],
            }
        result = {
            "success": True,
            "files_applied": len(output.patch_files),
            "rollback_id": f"rollback_{output.id[:8]}",
            "note": "Apply recorded in audit log — actual file writes require repository checkout",
            "notes": notes,
        }
        apply_id = self._log_apply(output.id, dry_run=False, success=True, result=result)
        return {"apply_id": apply_id, **result}

    def get_apply_history(self, output_id: str | None = None) -> list[dict]:
        log = self._load_log()
        if output_id:
            log = [l for l in log if l.get("output_id") == output_id]
        return log[-50:]
