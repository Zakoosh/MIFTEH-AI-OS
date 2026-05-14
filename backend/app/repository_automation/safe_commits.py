from __future__ import annotations
from datetime import datetime
from pathlib import Path
import subprocess
import json
from .repository_validation import RepositoryValidation


MEMORY_DIR = Path(__file__).parent.parent / "memory" / "repository_automation"


class SafeCommits:
    MAX_FILES_PER_COMMIT = 30
    REQUIRE_VALIDATION = True

    def __init__(self):
        self._log_path = MEMORY_DIR / "commit_log.json"
        self._validator = RepositoryValidation()
        MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    def _load_log(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        try:
            return json.loads(self._log_path.read_text())
        except Exception:
            return []

    def _save_log(self, data: list[dict]) -> None:
        self._log_path.write_text(json.dumps(data, indent=2, default=str))

    def _log_attempt(self, repo_path: str, files: list[str], message: str, success: bool, output: str) -> None:
        log = self._load_log()
        log.append({
            "repo_path": repo_path,
            "files": files,
            "message": message[:200],
            "success": success,
            "output": output[:500],
            "timestamp": datetime.utcnow().isoformat(),
        })
        self._save_log(log[-200:])

    def validate_commit(self, repo_path: str, files: list[str], message: str) -> tuple[bool, list[str]]:
        issues = []
        if not Path(repo_path).exists():
            issues.append(f"Repository path does not exist: {repo_path}")
        if not message or len(message.strip()) < 5:
            issues.append("Commit message too short")
        if len(files) > self.MAX_FILES_PER_COMMIT:
            issues.append(f"Too many files in commit (max {self.MAX_FILES_PER_COMMIT})")
        for f in files:
            ok, msg = self._validator.validate_file_path(f, repo_path)
            if not ok:
                issues.append(msg)
        return len(issues) == 0, issues

    def stage_files(self, repo_path: str, files: list[str]) -> tuple[bool, str]:
        try:
            args = ["git", "-C", repo_path, "add"] + files
            result = subprocess.run(args, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                return True, "Files staged"
            return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Git add timed out"
        except Exception as e:
            return False, str(e)

    def create_commit(self, repo_path: str, files: list[str], message: str, author: str = "MIFTEH AI OS") -> tuple[bool, str]:
        valid, issues = self.validate_commit(repo_path, files, message)
        if not valid:
            return False, f"Validation failed: {'; '.join(issues)}"

        staged, stage_msg = self.stage_files(repo_path, files)
        if not staged:
            self._log_attempt(repo_path, files, message, False, stage_msg)
            return False, f"Staging failed: {stage_msg}"

        full_message = f"{message}\n\n[MIFTEH AI OS - Automated commit by {author}]"
        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "commit", "-m", full_message],
                capture_output=True, text=True, timeout=30,
                env={"GIT_AUTHOR_NAME": author, "GIT_COMMITTER_NAME": author,
                     "GIT_AUTHOR_EMAIL": "ai@mifteh.com", "GIT_COMMITTER_EMAIL": "ai@mifteh.com",
                     "PATH": "/usr/bin:/bin:/usr/local/bin"},
            )
            success = result.returncode == 0
            output = result.stdout.strip() if success else result.stderr.strip()
            self._log_attempt(repo_path, files, message, success, output)
            return success, output
        except subprocess.TimeoutExpired:
            self._log_attempt(repo_path, files, message, False, "timeout")
            return False, "Git commit timed out"
        except Exception as e:
            self._log_attempt(repo_path, files, message, False, str(e))
            return False, str(e)

    def get_commit_history(self, repo_path: str, limit: int = 10) -> list[dict]:
        try:
            result = subprocess.run(
                ["git", "-C", repo_path, "log", f"--max-count={limit}", "--oneline", "--no-decorate"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                commits = []
                for line in result.stdout.strip().splitlines():
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        commits.append({"hash": parts[0], "message": parts[1]})
                return commits
            return []
        except Exception:
            return []
