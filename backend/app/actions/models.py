from pydantic import BaseModel, Field
from typing import Optional


class FileAction(BaseModel):
    type: str = "replace_in_file"
    path: str
    find: str
    replace: str


class ActionRequest(BaseModel):
    actions: list[FileAction]
    dry_run: bool = Field(default=False, description="Preview only, do not apply")


class ValidationIssue(BaseModel):
    action_index: int
    field: str
    message: str


class ActionPreview(BaseModel):
    action_index: int
    path: str
    valid: bool = True
    issues: list[str] = Field(default_factory=list)
    diff: str = ""
    find_found: bool = False


class BackupRecord(BaseModel):
    original_path: str
    backup_path: str
    created_at: str = ""


class ActionResult(BaseModel):
    action_index: int
    path: str
    status: str = "pending"
    applied: bool = False
    diff: str = ""
    patch: str = ""
    backup: Optional[BackupRecord] = None
    error: Optional[str] = None


class ExecutionResponse(BaseModel):
    execution_id: str = ""
    status: str = "pending"
    total_actions: int = 0
    applied_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    results: list[ActionResult] = Field(default_factory=list)
    created_at: str = ""


class ActionHistoryEntry(BaseModel):
    execution_id: str
    total_actions: int = 0
    applied_count: int = 0
    failed_count: int = 0
    status: str = ""
    created_at: str = ""


class RollbackRequest(BaseModel):
    execution_id: str
