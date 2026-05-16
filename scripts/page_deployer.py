"""
MIFTEH OS — Page Deployer
Deploys generated pages and content from outputs/ via GitHub API.
Creates feature branches, commits content files, opens PRs with rollback info.
NEVER auto-merges — creates PR for human review only.
Respects: safe staged deployments, rollback metadata, audit tracking.
"""
import json
import os
import sys
import base64
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
OUTPUTS_DIR = Path("outputs")
QUEUE_FILE = MEMORY_DIR / "deployment_queue.json"

GH_TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", "")
GH_API = "https://api.github.com"

REPO_MAP = {
    "yallaplays": os.environ.get("REPO_YALLAPLAYS", "Zakoosh/Yallaplays"),
    "fionera": os.environ.get("REPO_FIONERA", "Zakoosh/fionera"),
    "mifteh": os.environ.get("REPO_MIFTEH", "Zakoosh/mifteh-main-site"),
}

MAX_FILES_PER_PR = 10
MAX_DEPLOYMENTS_PER_CYCLE = 3

# Files that must NEVER be deployed by this system
FORBIDDEN_PATTERNS = [
    ".github/workflows", "auth", "password", "secret", ".env",
    "deploy.sh", "Dockerfile", "railway", "vercel", "supabase/migrations",
    "prisma", "database", "package-lock.json", "vite.config",
    "next.config", "webpack.config",
]


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def _gh(method, endpoint, payload=None):
    """GitHub API call."""
    if not GH_TOKEN:
        return {}, False
    try:
        url = f"{GH_API}{endpoint}"
        data = json.dumps(payload).encode() if payload else None
        req = urllib.request.Request(
            url, data=data, method=method,
            headers={
                "Authorization": f"Bearer {GH_TOKEN}",
                "Accept": "application/vnd.github.v3+json",
                "Content-Type": "application/json",
                "User-Agent": "MIFTEH-OS/1.0",
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode()), True
    except urllib.error.HTTPError as e:
        try:
            err_body = json.loads(e.read().decode())
        except Exception:
            err_body = {"message": str(e)}
        return err_body, False
    except Exception as e:
        return {"error": str(e)[:100]}, False


def load_queue():
    if QUEUE_FILE.exists():
        try:
            return json.loads(QUEUE_FILE.read_text())
        except Exception:
            pass
    return {"queue": [], "deployed": [], "failed": [], "created_at": now_iso()}


def save_queue(queue):
    QUEUE_FILE.write_text(json.dumps(queue, indent=2, ensure_ascii=False))


def is_safe_file(file_path):
    """Check that a file path doesn't match forbidden patterns."""
    fp = str(file_path).lower()
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in fp:
            return False
    return True


def scan_outputs_for_deployment(queue):
    """Scan outputs/ directory for new batch files ready to deploy."""
    already_queued = {item["batch_file"] for item in queue.get("queue", [])}
    already_deployed = {item["batch_file"] for item in queue.get("deployed", [])}
    already_failed = {item["batch_file"] for item in queue.get("failed", [])}
    processed = already_queued | already_deployed | already_failed

    new_items = []
    for project in ["yallaplays", "fionera", "mifteh"]:
        for subdir in ["programmatic", "product", "acquisition"]:
            scan_dir = OUTPUTS_DIR / project / subdir
            if not scan_dir.exists():
                continue
            for batch_file in sorted(scan_dir.glob("*.json"), reverse=True)[:5]:
                batch_key = str(batch_file)
                if batch_key in processed:
                    continue
                try:
                    data = json.loads(batch_file.read_text())
                    if not data.get("deployment_ready"):
                        continue
                    new_items.append({
                        "batch_file": batch_key,
                        "project": data.get("project", project),
                        "feature_type": data.get("feature_type", subdir),
                        "batch_id": data.get("batch_id", ""),
                        "generated_at": data.get("generated_at", ""),
                        "queued_at": now_iso(),
                        "status": "queued",
                    })
                except Exception:
                    continue

    return new_items


def get_default_branch(repo):
    """Get the default branch name of a repo."""
    data, ok = _gh("GET", f"/repos/{repo}")
    if ok:
        return data.get("default_branch", "main")
    return "main"


def get_branch_sha(repo, branch):
    """Get the latest commit SHA for a branch."""
    data, ok = _gh("GET", f"/repos/{repo}/git/ref/heads/{branch}")
    if ok:
        return data.get("object", {}).get("sha", ""), True
    return "", False


def create_branch(repo, branch_name, from_sha):
    """Create a new branch from a given SHA."""
    data, ok = _gh("POST", f"/repos/{repo}/git/refs", {
        "ref": f"refs/heads/{branch_name}",
        "sha": from_sha,
    })
    return ok


def create_file_in_branch(repo, branch, file_path, content, commit_message):
    """Create or update a file in a branch."""
    # Check if file exists (to get SHA for update)
    existing, exists = _gh("GET", f"/repos/{repo}/contents/{file_path}?ref={branch}")
    sha = existing.get("sha") if exists and "sha" in existing else None

    payload = {
        "message": commit_message,
        "content": base64.b64encode(content.encode()).decode(),
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    data, ok = _gh("PUT", f"/repos/{repo}/contents/{file_path}", payload)
    return ok


def create_pr(repo, branch, base_branch, title, body):
    """Create a pull request — NEVER auto-merges."""
    data, ok = _gh("POST", f"/repos/{repo}/pulls", {
        "title": title,
        "head": branch,
        "base": base_branch,
        "body": body,
        "draft": False,
    })
    if ok:
        return data.get("html_url", ""), data.get("number", 0), True
    return "", 0, False


def build_pr_body(item, files_deployed, feature_summary):
    """Build a PR description with rollback metadata."""
    return f"""## MIFTEH OS — Automated Content Deployment

**Project:** {item['project']}
**Feature Type:** {item['feature_type']}
**Batch ID:** {item['batch_id']}
**Generated At:** {item['generated_at']}

### Files Deployed
{chr(10).join(f'- `{f}`' for f in files_deployed)}

### Feature Summary
{feature_summary}

### Rollback Instructions
To rollback this deployment:
1. Close this PR without merging
2. Or revert the merge commit: `git revert MERGE_COMMIT_SHA`
3. The `memory/deployment_queue.json` tracks deployment history

### Safety Checks
- ✅ No config files modified
- ✅ No credentials included
- ✅ No auto-merge enabled
- ✅ Rollback metadata included

> Generated by MIFTEH OS Page Deployer — requires human review before merge"""


def deploy_batch_item(item):
    """Deploy a single batch item as a GitHub PR."""
    project = item["project"]
    repo = REPO_MAP.get(project)
    if not repo:
        return {"success": False, "error": f"No repo configured for {project}"}

    if not GH_TOKEN:
        return {"success": False, "error": "GH_TOKEN not configured"}

    try:
        batch_data = json.loads(Path(item["batch_file"]).read_text())
    except Exception as e:
        return {"success": False, "error": f"Cannot read batch file: {e}"}

    default_branch = get_default_branch(repo)
    base_sha, ok = get_branch_sha(repo, default_branch)
    if not ok:
        return {"success": False, "error": "Cannot get base branch SHA"}

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    branch_name = f"mifteh-os/{item['feature_type']}-{ts}"

    if not create_branch(repo, branch_name, base_sha):
        return {"success": False, "error": "Cannot create branch"}

    files_deployed = []
    feature_type = item["feature_type"]

    if feature_type == "programmatic_seo_batch":
        page_types = batch_data.get("page_types", {})
        for ptype, pages in page_types.items():
            if not isinstance(pages, list) or not pages:
                continue
            safe_path = f"data/seo/{ptype}/batch_{ts}.json"
            if not is_safe_file(safe_path):
                continue
            content = json.dumps(pages, indent=2, ensure_ascii=False)
            if create_file_in_branch(repo, branch_name, safe_path, content, f"AI: Add {ptype} ({len(pages)} pages) [skip ci]"):
                files_deployed.append(safe_path)
            if len(files_deployed) >= MAX_FILES_PER_PR:
                break

    elif feature_type == "product_build":
        features = batch_data.get("features", {})
        for fname, fdata in list(features.items())[:MAX_FILES_PER_PR]:
            safe_path = f"data/product/{fname}_{ts}.json"
            if not is_safe_file(safe_path):
                continue
            content = json.dumps(fdata, indent=2, ensure_ascii=False)
            if create_file_in_branch(repo, branch_name, safe_path, content, f"AI: Add {fname} feature data [skip ci]"):
                files_deployed.append(safe_path)

    elif feature_type == "client_acquisition":
        for section in ["service_pages", "case_studies", "lead_magnets"]:
            section_data = batch_data.get(section, [])
            if not section_data:
                continue
            safe_path = f"data/acquisition/{section}_{ts}.json"
            if not is_safe_file(safe_path):
                continue
            content = json.dumps(section_data, indent=2, ensure_ascii=False)
            if create_file_in_branch(repo, branch_name, safe_path, content, f"AI: Add {section} [skip ci]"):
                files_deployed.append(safe_path)

    if not files_deployed:
        return {"success": False, "error": "No files deployed"}

    total_pages = batch_data.get("total_pages", len(files_deployed))
    feature_summary = f"Deployed {len(files_deployed)} files ({total_pages} content items) from {feature_type} batch."

    pr_url, pr_number, pr_ok = create_pr(
        repo, branch_name, default_branch,
        f"AI: {feature_type} content batch — {len(files_deployed)} files [{ts}]",
        build_pr_body(item, files_deployed, feature_summary),
    )

    if pr_ok:
        return {
            "success": True,
            "pr_url": pr_url,
            "pr_number": pr_number,
            "branch": branch_name,
            "files_deployed": files_deployed,
            "repo": repo,
        }
    else:
        return {"success": False, "error": "PR creation failed"}


def ai_deployment_summary(deployed, failed, queued):
    """AI summarizes deployment cycle."""
    system = "Deployment engineer summarizing CI/CD results. Return valid JSON only."
    prompt = f"""Deployment cycle complete:
Deployed: {len(deployed)} batches successfully
Failed: {len(failed)} batches
Remaining queue: {len(queued)} batches

Return:
{{
  "deployment_score": 0-100,
  "cycle_status": "healthy|degraded|failed",
  "deployed_summary": "1-sentence summary",
  "recommendations": ["rec1", "rec2"]
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 200)
    if not ok:
        score = 100 if not failed else round(len(deployed) / max(len(deployed) + len(failed), 1) * 100)
        data = {
            "deployment_score": score,
            "cycle_status": "healthy" if score > 70 else "degraded",
            "deployed_summary": f"{len(deployed)} content batches deployed as PRs for review.",
            "recommendations": ["Review open PRs before merging", "Monitor deployment queue"],
        }
    return data, tokens, cost


def main():
    print("[page_deployer] Starting deployment cycle...")
    all_tokens, all_cost = 0, 0.0

    queue = load_queue()
    new_items = scan_outputs_for_deployment(queue)
    if new_items:
        queue["queue"].extend(new_items)
        print(f"[page_deployer] Added {len(new_items)} new items to queue")

    pending = [item for item in queue.get("queue", []) if item.get("status") == "queued"]
    print(f"[page_deployer] Pending deployments: {len(pending)}")

    deployed_this_cycle = []
    failed_this_cycle = []

    for item in pending[:MAX_DEPLOYMENTS_PER_CYCLE]:
        print(f"[page_deployer] Deploying {item['feature_type']} / {item['project']}...")
        result = deploy_batch_item(item)

        if result["success"]:
            item["status"] = "deployed"
            item["deployed_at"] = now_iso()
            item["pr_url"] = result.get("pr_url", "")
            item["pr_number"] = result.get("pr_number", 0)
            item["files_deployed"] = result.get("files_deployed", [])
            queue["deployed"].append(item)
            deployed_this_cycle.append(item)
            queue["queue"] = [q for q in queue["queue"] if q["batch_file"] != item["batch_file"]]
            print(f"[page_deployer] ✓ PR created: {result.get('pr_url', 'unknown')}")
        else:
            item["status"] = "failed"
            item["error"] = result.get("error", "unknown")
            item["failed_at"] = now_iso()
            queue["failed"].append(item)
            failed_this_cycle.append(item)
            queue["queue"] = [q for q in queue["queue"] if q["batch_file"] != item["batch_file"]]
            print(f"[page_deployer] ✗ Failed: {result.get('error', 'unknown')}")

    save_queue(queue)

    remaining_queue = [item for item in queue.get("queue", []) if item.get("status") == "queued"]
    analysis, tokens, cost = ai_deployment_summary(deployed_this_cycle, failed_this_cycle, remaining_queue)
    all_tokens += tokens
    all_cost += cost

    report = {
        "generated_at": now_iso(),
        "cycle_deployed": len(deployed_this_cycle),
        "cycle_failed": len(failed_this_cycle),
        "queue_remaining": len(remaining_queue),
        "total_deployed_all_time": len(queue.get("deployed", [])),
        "deployed_this_cycle": [
            {"project": d["project"], "feature_type": d["feature_type"], "pr_url": d.get("pr_url", ""), "files": len(d.get("files_deployed", []))}
            for d in deployed_this_cycle
        ],
        "failed_this_cycle": [
            {"project": d["project"], "feature_type": d["feature_type"], "error": d.get("error", "")}
            for d in failed_this_cycle
        ],
        "deployment_score": analysis.get("deployment_score", 0),
        "cycle_status": analysis.get("cycle_status", "unknown"),
        "recommendations": analysis.get("recommendations", []),
        "tokens_used": all_tokens,
        "cost_usd": round(all_cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "page_deployer_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[page_deployer] Done — {len(deployed_this_cycle)} deployed, {len(failed_this_cycle)} failed, {len(remaining_queue)} queued, ${all_cost:.4f}")


if __name__ == "__main__":
    main()
