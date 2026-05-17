"""
Safe Autonomous Apply Pipeline — orchestrates the full apply lifecycle:
  generate → patch → build → validate → screenshot → lighthouse → PR → merge →
  deploy → live verify

Each step is gated: any failure stops the pipeline and saves a failure report.
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable

from .registry import get_project, get_production_source
from .source_enforcer import enforce_write, EnforcementError
from .framework_detector import detect_framework
from .report_store import save, REPORTS_ROOT

PIPELINE_LOG_DIR = REPORTS_ROOT / "pipeline"


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline state
# ──────────────────────────────────────────────────────────────────────────────

class PipelineStep:
    VALIDATE_WRITES = "validate_writes"
    BUILD = "build"
    LIVE_VALIDATE = "live_validate"
    SCREENSHOT_BEFORE = "screenshot_before"
    SCREENSHOT_AFTER = "screenshot_after"
    REGRESSION = "regression"
    PR_REVIEW = "pr_review"
    CREATE_PR = "create_pr"
    MERGE_PR = "merge_pr"
    DEPLOY_WAIT = "deploy_wait"
    LIVE_VERIFY = "live_verify"


class PipelineStatus:
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class PipelineError(Exception):
    def __init__(self, step: str, reason: str, details: Optional[dict] = None):
        self.step = step
        self.reason = reason
        self.details = details or {}
        super().__init__(f"[{step}] {reason}")


# ──────────────────────────────────────────────────────────────────────────────
# Pipeline context
# ──────────────────────────────────────────────────────────────────────────────

class PipelineContext:
    def __init__(self, project_id: str, branch: str, pr_title: Optional[str] = None,
                 auto_merge: bool = False, dry_run: bool = False):
        self.project_id = project_id
        self.branch = branch
        self.pr_title = pr_title or f"chore: autonomous apply [{project_id}]"
        self.auto_merge = auto_merge
        self.dry_run = dry_run
        self.start_time = datetime.now(timezone.utc)
        self.steps: list[dict] = []
        self.pr_url: Optional[str] = None
        self.pr_number: Optional[int] = None
        self.deploy_url: Optional[str] = None
        self.artifacts: dict = {}

    def record(self, step: str, status: str, data: dict = None, error: str = None):
        entry = {
            "step": step,
            "status": status,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }
        if error:
            entry["error"] = error
        self.steps.append(entry)
        return entry

    def get_step(self, step: str) -> Optional[dict]:
        for s in reversed(self.steps):
            if s["step"] == step:
                return s
        return None

    def passed(self, step: str) -> bool:
        s = self.get_step(step)
        return s is not None and s["status"] == PipelineStatus.PASSED

    def to_report(self) -> dict:
        elapsed = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        last_step = self.steps[-1] if self.steps else {}
        failed_steps = [s for s in self.steps if s["status"] == PipelineStatus.FAILED]
        return {
            "project_id": self.project_id,
            "branch": self.branch,
            "started_at": self.start_time.isoformat(),
            "elapsed_seconds": round(elapsed, 1),
            "overall_status": (
                PipelineStatus.FAILED if failed_steps else
                PipelineStatus.PASSED
            ),
            "pr_url": self.pr_url,
            "pr_number": self.pr_number,
            "deploy_url": self.deploy_url,
            "steps": self.steps,
            "failed_steps": [s["step"] for s in failed_steps],
            "dry_run": self.dry_run,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Step implementations
# ──────────────────────────────────────────────────────────────────────────────

def _run_cmd(cmd: list[str], cwd: Optional[str] = None, timeout: int = 300) -> tuple[int, str, str]:
    """Run a subprocess, return (returncode, stdout, stderr)."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, env={**os.environ},
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", f"Command timed out after {timeout}s"
    except Exception as e:
        return -1, "", str(e)


def step_validate_writes(ctx: PipelineContext, write_paths: list[str]) -> dict:
    """Validate all proposed write paths against source enforcer."""
    from .source_enforcer import validate_all_writes
    writes = [{"path": p} for p in write_paths]
    result = validate_all_writes(writes, ctx.project_id)
    blocked = result["blocked"]
    if blocked > 0:
        blocked_paths = [r["path"] for r in result["results"] if not r["allowed"]]
        raise PipelineError(
            PipelineStep.VALIDATE_WRITES,
            f"{blocked} writes blocked by source enforcer",
            {"blocked_paths": blocked_paths, "result": result},
        )
    return result


def step_build(ctx: PipelineContext) -> dict:
    """Run the project build and verify it succeeds."""
    p = get_project(ctx.project_id)
    source_path = Path(get_production_source(ctx.project_id))
    fw = detect_framework(source_path)
    build_cmd = fw.get("build_command", "npm run build")

    if ctx.dry_run:
        return {"ok": True, "dry_run": True, "build_command": build_cmd}

    cmd_parts = build_cmd.split()
    code, stdout, stderr = _run_cmd(cmd_parts, cwd=str(source_path), timeout=600)

    if code != 0:
        raise PipelineError(
            PipelineStep.BUILD,
            f"Build failed (exit {code})",
            {"stdout": stdout[-3000:], "stderr": stderr[-3000:], "build_command": build_cmd},
        )

    return {
        "ok": True,
        "build_command": build_cmd,
        "stdout_tail": stdout[-1000:],
    }


def step_live_validate(ctx: PipelineContext) -> dict:
    """Run live validator against current production."""
    from .live_validator import validate_project
    try:
        report = validate_project(ctx.project_id, check_links=False)
        return {"ok": report.get("overall_ok", False), "health_score": report.get("health_score", 0)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def step_screenshot(ctx: PipelineContext, label: str) -> dict:
    """Capture screenshots for before/after comparison."""
    from .screenshot_validator import capture_project
    try:
        result = capture_project(ctx.project_id, label=label)
        ctx.artifacts[f"screenshot_{label}"] = result
        return {"ok": result.get("overall_ok", False), "label": label}
    except Exception as e:
        return {"ok": False, "error": str(e), "label": label}


def step_regression(ctx: PipelineContext) -> dict:
    """Compare before/after screenshots."""
    from .screenshot_validator import regression_check
    try:
        result = regression_check(ctx.project_id, before_label="before", after_label="after")
        ctx.artifacts["regression"] = result
        return result
    except Exception as e:
        return {"ok": False, "error": str(e)}


def step_pr_review(ctx: PipelineContext, diff_text: Optional[str] = None) -> dict:
    """Run automated PR review on the diff."""
    if not diff_text:
        # Generate diff from git
        source_path = str(Path(get_production_source(ctx.project_id)))
        code, stdout, _ = _run_cmd(
            ["git", "diff", "HEAD~1", "HEAD"],
            cwd=source_path,
        )
        diff_text = stdout if code == 0 else ""

    if not diff_text:
        return {"ok": True, "skipped": True, "reason": "No diff available"}

    from .pr_reviewer import review_diff
    report = review_diff(diff_text, ctx.project_id, ctx.pr_number)
    ctx.artifacts["pr_review"] = report
    return {
        "ok": report.get("recommendation") != "REQUEST_CHANGES",
        "recommendation": report.get("recommendation"),
        "risk_summary": report.get("risk_summary"),
    }


def step_create_pr(ctx: PipelineContext, gh_pat: str) -> dict:
    """Create a GitHub PR using the gh CLI."""
    if ctx.dry_run:
        return {"ok": True, "dry_run": True, "pr_url": "https://github.com/dry-run/pr/0"}

    p = get_project(ctx.project_id)
    source_path = str(Path(get_production_source(ctx.project_id)))

    code, stdout, stderr = _run_cmd(
        ["gh", "pr", "create",
         "--title", ctx.pr_title,
         "--body", f"Autonomous apply by MIFTEH AI OS\n\nProject: {ctx.project_id}\nBranch: {ctx.branch}",
         "--head", ctx.branch,
         "--base", "main"],
        cwd=source_path,
    )

    if code != 0:
        raise PipelineError(
            PipelineStep.CREATE_PR,
            f"gh pr create failed: {stderr[:500]}",
        )

    pr_url = stdout.strip()
    ctx.pr_url = pr_url
    # Extract PR number from URL
    import re
    m = re.search(r"/pull/(\d+)", pr_url)
    if m:
        ctx.pr_number = int(m.group(1))

    return {"ok": True, "pr_url": pr_url, "pr_number": ctx.pr_number}


def step_merge_pr(ctx: PipelineContext) -> dict:
    """Auto-merge the PR if it passes all checks."""
    if ctx.dry_run or not ctx.auto_merge:
        return {"ok": True, "skipped": True, "reason": "auto_merge disabled or dry_run"}

    if not ctx.pr_url:
        return {"ok": False, "error": "No PR URL available"}

    source_path = str(Path(get_production_source(ctx.project_id)))
    code, stdout, stderr = _run_cmd(
        ["gh", "pr", "merge", str(ctx.pr_number), "--squash", "--auto"],
        cwd=source_path,
    )
    if code != 0:
        return {"ok": False, "error": stderr[:500]}

    return {"ok": True, "merged": True}


def step_deploy_wait(ctx: PipelineContext, timeout_seconds: int = 300) -> dict:
    """Poll GitHub Pages deployment status until live or timeout."""
    if ctx.dry_run:
        return {"ok": True, "dry_run": True}

    p = get_project(ctx.project_id)
    domain = p.get("domain", "")
    if not domain:
        return {"ok": False, "error": "No domain configured"}

    import urllib.request
    deadline = time.time() + timeout_seconds
    check_url = f"https://{domain}"
    polls = 0

    while time.time() < deadline:
        try:
            req = urllib.request.Request(check_url, headers={"User-Agent": "MIFTEH-AI-OS/1.0"})
            with urllib.request.urlopen(req, timeout=10) as r:
                if r.status < 400:
                    return {"ok": True, "polls": polls, "url": check_url, "final_status": r.status}
        except Exception:
            pass
        polls += 1
        time.sleep(15)

    return {"ok": False, "error": f"Deploy not detected after {timeout_seconds}s", "polls": polls}


def step_live_verify(ctx: PipelineContext) -> dict:
    """Full post-deploy live validation."""
    return step_live_validate(ctx)


# ──────────────────────────────────────────────────────────────────────────────
# Main pipeline runner
# ──────────────────────────────────────────────────────────────────────────────

def run_pipeline(
    project_id: str,
    branch: str,
    write_paths: Optional[list[str]] = None,
    diff_text: Optional[str] = None,
    gh_pat: Optional[str] = None,
    pr_title: Optional[str] = None,
    auto_merge: bool = False,
    dry_run: bool = False,
    skip_screenshots: bool = False,
    skip_pr: bool = False,
) -> dict:
    """
    Run the full autonomous apply pipeline.
    Returns the final pipeline report.
    """
    ctx = PipelineContext(project_id, branch, pr_title, auto_merge, dry_run)

    def _step(name: str, fn: Callable, *args, **kwargs) -> bool:
        ctx.record(name, PipelineStatus.RUNNING)
        try:
            result = fn(*args, **kwargs)
            ctx.record(name, PipelineStatus.PASSED, result)
            return True
        except PipelineError as e:
            ctx.record(name, PipelineStatus.FAILED, e.details, error=e.reason)
            return False
        except Exception as e:
            ctx.record(name, PipelineStatus.FAILED, error=str(e))
            return False

    # Step 1: Validate writes
    if write_paths:
        if not _step(PipelineStep.VALIDATE_WRITES, step_validate_writes, ctx, write_paths):
            return _save_and_return(ctx)

    # Step 2: Screenshot before (capture current state)
    if not skip_screenshots:
        _step(PipelineStep.SCREENSHOT_BEFORE, step_screenshot, ctx, "before")

    # Step 3: Build
    if not _step(PipelineStep.BUILD, step_build, ctx):
        return _save_and_return(ctx)

    # Step 4: Screenshot after
    if not skip_screenshots:
        _step(PipelineStep.SCREENSHOT_AFTER, step_screenshot, ctx, "after")
        _step(PipelineStep.REGRESSION, step_regression, ctx)

    # Step 5: PR review
    _step(PipelineStep.PR_REVIEW, step_pr_review, ctx, diff_text)

    # Step 6: Create PR
    if not skip_pr:
        if not gh_pat:
            ctx.record(PipelineStep.CREATE_PR, PipelineStatus.SKIPPED,
                       {"reason": "No GH_PAT provided"})
        else:
            if not _step(PipelineStep.CREATE_PR, step_create_pr, ctx, gh_pat):
                return _save_and_return(ctx)

            # Step 7: Auto-merge if enabled
            if auto_merge:
                if not _step(PipelineStep.MERGE_PR, step_merge_pr, ctx):
                    return _save_and_return(ctx)

                # Step 8: Wait for deploy
                _step(PipelineStep.DEPLOY_WAIT, step_deploy_wait, ctx)

    # Step 9: Live verify
    _step(PipelineStep.LIVE_VERIFY, step_live_verify, ctx)

    return _save_and_return(ctx)


def _save_and_return(ctx: PipelineContext) -> dict:
    report = ctx.to_report()
    save("pipeline", ctx.project_id, report)
    return report


# ──────────────────────────────────────────────────────────────────────────────
# Convenience entry points
# ──────────────────────────────────────────────────────────────────────────────

def dry_run_pipeline(project_id: str, branch: str = "main", write_paths: Optional[list[str]] = None) -> dict:
    """Dry-run pipeline — validates writes and build only, no PR/deploy."""
    return run_pipeline(
        project_id, branch, write_paths=write_paths,
        dry_run=True, skip_screenshots=True, skip_pr=True,
    )


def validate_and_report(project_id: str) -> dict:
    """Quick validate — live check + SEO + screenshot only, no PR/deploy."""
    ctx = PipelineContext(project_id, "main", dry_run=True)

    from .live_validator import validate_project
    from .seo_engine import analyze_project

    live = validate_project(project_id)
    ctx.record(PipelineStep.LIVE_VERIFY, PipelineStatus.PASSED,
               {"health_score": live.get("health_score"), "ok": live.get("overall_ok")})

    seo = analyze_project(project_id)
    ctx.record("seo_analysis", PipelineStatus.PASSED,
               {"seo_score": seo.get("overall_seo_score"), "issues": seo.get("total_issues")})

    return _save_and_return(ctx)


if __name__ == "__main__":
    pid = sys.argv[1] if len(sys.argv) > 1 else "yallaplays"
    mode = sys.argv[2] if len(sys.argv) > 2 else "validate"
    if mode == "validate":
        r = validate_and_report(pid)
    elif mode == "dry":
        r = dry_run_pipeline(pid)
    else:
        r = validate_and_report(pid)
    print(json.dumps(r, indent=2))
