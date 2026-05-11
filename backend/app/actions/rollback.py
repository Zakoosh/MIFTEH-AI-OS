import shutil
from datetime import datetime
from pathlib import Path

from app.actions.models import BackupRecord
from app.actions.schemas import BACKUP_DIR_NAME
from app.projects.workspace import get_workspace_root


def _get_backup_dir() -> Path:
    workspace_root = get_workspace_root()
    backup_dir = workspace_root / BACKUP_DIR_NAME
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def create_backup(file_path: str, execution_id: str) -> BackupRecord:
    workspace_root = get_workspace_root()
    absolute_path = (workspace_root / file_path).resolve()

    if not absolute_path.is_file():
        return BackupRecord(
            original_path=file_path,
            backup_path="",
            created_at=datetime.now().isoformat(),
        )

    backup_dir = _get_backup_dir() / execution_id
    backup_dir.mkdir(parents=True, exist_ok=True)

    safe_name = file_path.replace("/", "__").replace("\\", "__")
    backup_file = backup_dir / safe_name

    shutil.copy2(str(absolute_path), str(backup_file))

    return BackupRecord(
        original_path=file_path,
        backup_path=str(backup_file),
        created_at=datetime.now().isoformat(),
    )


def restore_backup(backup: BackupRecord) -> bool:
    if not backup.backup_path:
        return False

    backup_path = Path(backup.backup_path)
    if not backup_path.is_file():
        return False

    workspace_root = get_workspace_root()
    original_path = (workspace_root / backup.original_path).resolve()

    try:
        shutil.copy2(str(backup_path), str(original_path))
        return True
    except Exception:
        return False


def restore_execution(execution_id: str, backups: list[BackupRecord]) -> dict:
    restored = 0
    failed = 0
    details: list[dict] = []

    for backup in backups:
        success = restore_backup(backup)
        if success:
            restored += 1
            details.append({"path": backup.original_path, "status": "restored"})
        else:
            failed += 1
            details.append({"path": backup.original_path, "status": "failed"})

    return {
        "execution_id": execution_id,
        "restored": restored,
        "failed": failed,
        "details": details,
    }
