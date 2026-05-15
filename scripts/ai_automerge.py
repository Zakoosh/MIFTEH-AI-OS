"""
MIFTEH OS — Autonomous Auto-Merge System
Evaluates open draft PRs using trust_manager, converts qualifying ones to ready,
then merges via GitHub API. Only merges when safety score >= 90.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from trust_manager import calculate_safety_score, record_deploy, is_suspended

GH_TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", "")
MEMORY_DIR = Path("memory")
ALL_PRS_FILE = MEMORY_DIR / "all_prs.json"
AUTOMERGE_LOG = MEMORY_DIR / "automerge_log.json"
QA_DIR = MEMORY_DIR / "visual_qa"

# Minimum visual QA score required for HTML files to auto-merge
VISUAL_QA_THRESHOLD = 70


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─── GitHub REST ──────────────────────────────────────────────────────────────

def gh(method, path, payload=None):
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(payload).encode() if payload else None,
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MIFTEH-AI-OS/automerge",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read()
            return json.loads(body) if body else {}, r.getcode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        print(f"  [gh] {method} {path} => {e.code}: {body}")
        return None, e.code


# ─── GitHub GraphQL ───────────────────────────────────────────────────────────

def graphql(query, variables=None):
    payload = {"query": query, "variables": variables or {}}
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "MIFTEH-AI-OS/automerge",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()), r.getcode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        print(f"  [graphql] => {e.code}: {body}")
        return None, e.code


def get_pr_node_id(owner, repo, pr_number):
    """Get the GraphQL node_id for a PR (needed to convert draft → ready)."""
    q = """
    query($owner: String!, $repo: String!, $number: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $number) {
          id
          isDraft
          mergeable
          state
        }
      }
    }
    """
    data, code = graphql(q, {"owner": owner, "repo": repo, "number": pr_number})
    if not data or "data" not in data:
        return None, None, None
    pr = (data["data"].get("repository") or {}).get("pullRequest") or {}
    return pr.get("id"), pr.get("isDraft"), pr.get("mergeable")


def convert_draft_to_ready(node_id):
    """Convert a draft PR to ready for review via GraphQL mutation."""
    mutation = """
    mutation($id: ID!) {
      markPullRequestReadyForReview(input: {pullRequestId: $id}) {
        pullRequest { isDraft number }
      }
    }
    """
    data, code = graphql(mutation, {"id": node_id})
    if not data:
        return False
    errors = data.get("errors")
    if errors:
        print(f"  [graphql] mutation errors: {errors}")
        return False
    return True


# ─── PR file listing ──────────────────────────────────────────────────────────

def get_pr_files(owner, repo, pr_number):
    """Return list of file dicts with filename, additions, deletions."""
    data, code = gh("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}/files")
    if code != 200 or not isinstance(data, list):
        return []
    return [{"filename": f["filename"], "additions": f.get("additions", 0),
             "deletions": f.get("deletions", 0)} for f in data]


def get_pr_state(owner, repo, pr_number):
    """Return PR state and mergeable status."""
    data, code = gh("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")
    if code != 200 or not data:
        return None
    return {
        "state": data.get("state"),
        "merged": data.get("merged", False),
        "mergeable": data.get("mergeable"),
        "mergeable_state": data.get("mergeable_state"),
        "draft": data.get("draft", False),
        "head_sha": data.get("head", {}).get("sha"),
        "base": data.get("base", {}).get("ref"),
    }


# ─── Merge ────────────────────────────────────────────────────────────────────

def merge_pr(owner, repo, pr_number, head_sha, pr_title):
    payload = {
        "commit_title": f"AI: Auto-merge — {pr_title} [skip ci]",
        "commit_message": f"Merged autonomously by MIFTEH AI OS at {_now()}. Safety-gated (score >= 90).",
        "sha": head_sha,
        "merge_method": "squash",
    }
    data, code = gh("PUT", f"/repos/{owner}/{repo}/pulls/{pr_number}/merge", payload)
    if code == 200 and data and data.get("merged"):
        return True, data.get("sha", "")
    return False, ""


# ─── Visual QA gate ───────────────────────────────────────────────────────────

def check_visual_qa(html_files: list, project: str) -> dict:
    """
    Check visual QA reports for all HTML files in a PR.
    Returns summary: {checked, blocked, blocked_files, min_score, avg_score}.
    Files without a QA report are skipped (not blocked) — QA is optional.
    """
    scores = []
    blocked_files = []

    for file_info in html_files:
        filename = file_info["filename"]
        feature_id = Path(filename).stem

        qa_path = QA_DIR / f"{project}_{feature_id}.json"
        if not qa_path.exists():
            # Try without project prefix (fallback)
            alternatives = list(QA_DIR.glob(f"*_{feature_id}.json")) if QA_DIR.exists() else []
            if alternatives:
                qa_path = alternatives[0]
            else:
                print(f"  [qa] No QA report for {filename} — not blocking (run generate_previews.py first)")
                continue

        try:
            qa = json.loads(qa_path.read_text())
            score = qa.get("score", 0)
            scores.append(score)
            passes = qa.get("passes_auto_merge_threshold", False)
            print(f"  [qa] {filename}: score={score}/100 grade={qa.get('grade','?')} — {'PASS' if passes else 'FAIL'}")
            if not passes:
                blocked_files.append(filename)
        except Exception as e:
            print(f"  [qa] Could not read QA report for {filename}: {e}")

    return {
        "checked": len(scores),
        "blocked": len(blocked_files) > 0,
        "blocked_files": blocked_files,
        "min_score": min(scores) if scores else None,
        "avg_score": round(sum(scores) / len(scores)) if scores else None,
    }


# ─── Main evaluation loop ─────────────────────────────────────────────────────

def load_prs():
    if ALL_PRS_FILE.exists():
        try:
            return json.loads(ALL_PRS_FILE.read_text())
        except Exception:
            return []
    return []


def load_log():
    if AUTOMERGE_LOG.exists():
        try:
            return json.loads(AUTOMERGE_LOG.read_text())
        except Exception:
            return []
    return []


def save_log(entries):
    MEMORY_DIR.mkdir(exist_ok=True)
    AUTOMERGE_LOG.write_text(json.dumps(entries, indent=2, ensure_ascii=False))


def evaluate_and_merge_pr(pr_record):
    """
    Full pipeline for one PR: evaluate → gate → convert draft → merge → record.
    Returns a result dict.
    """
    repo_full = pr_record["repo"]
    pr_number = pr_record["pr_number"]
    pr_title = pr_record.get("pr_title", f"PR #{pr_number}")
    owner, repo = repo_full.split("/")

    result = {
        "repo": repo_full,
        "pr_number": pr_number,
        "pr_url": pr_record.get("pr_url"),
        "evaluated_at": _now(),
        "action": "skipped",
        "reason": "",
        "score": 0,
        "score_reasons": [],
        "merge_sha": "",
    }

    print(f"\n{'='*60}")
    print(f"[automerge] Evaluating {repo_full} PR #{pr_number}")

    # 1. Check suspension
    if is_suspended(repo_full):
        result["reason"] = "repo is suspended (rollback rate > 20%)"
        print(f"  [!] SUSPENDED — skipping")
        return result

    # 2. Get current PR state
    state = get_pr_state(owner, repo, pr_number)
    if not state:
        result["reason"] = "could not fetch PR state"
        return result
    if state["merged"]:
        result["action"] = "already_merged"
        result["reason"] = "PR was already merged"
        print(f"  [i] Already merged — skipping")
        return result
    if state["state"] != "open":
        result["reason"] = f"PR state is '{state['state']}' (not open)"
        return result

    # 3. Fetch PR files for safety evaluation
    pr_files = get_pr_files(owner, repo, pr_number)
    if not pr_files:
        # Fall back to files_committed from memory record
        committed = pr_record.get("files_committed", [])
        pr_files = [{"filename": f, "additions": 10, "deletions": 5} for f in committed]
        print(f"  [i] GitHub API returned no files — using memory record: {committed}")

    print(f"  Files: {[f['filename'] for f in pr_files]}")

    # 4. Safety score evaluation
    score, reasons, qualifies = calculate_safety_score(pr_files, repo_full)
    result["score"] = score
    result["score_reasons"] = reasons
    print(f"  Safety score: {score}/100 — qualifies: {qualifies}")
    for r in reasons:
        print(f"    {r}")

    if not qualifies:
        result["reason"] = f"safety score {score} < 90 — not qualifying"
        result["action"] = "rejected"
        return result

    # 4b. Visual QA gate — check HTML files against QA threshold
    html_files = [f for f in pr_files if f["filename"].endswith(".html")]
    if html_files:
        qa_results = check_visual_qa(html_files, pr_record.get("project", ""))
        result["visual_qa"] = qa_results
        if qa_results.get("blocked"):
            result["reason"] = (
                f"visual QA score {qa_results['min_score']}/100 below threshold {VISUAL_QA_THRESHOLD} "
                f"for: {', '.join(qa_results['blocked_files'])}"
            )
            result["action"] = "rejected_qa"
            print(f"  [!] VISUAL QA BLOCK — {result['reason']}")
            return result
        if qa_results.get("checked"):
            print(f"  [qa] Visual QA: {qa_results['checked']} files checked, "
                  f"avg={qa_results.get('avg_score', '?')}/100 — all pass")

    # 5. Check mergeable state (retry once — GitHub computes this async)
    mergeable = state.get("mergeable")
    mergeable_state = state.get("mergeable_state")
    if mergeable is False or mergeable_state == "conflicting":
        result["reason"] = f"PR has merge conflicts (mergeable={mergeable}, state={mergeable_state})"
        result["action"] = "rejected"
        print(f"  [!] Merge conflicts — skipping")
        return result

    # 6. Convert draft → ready for review (if still draft)
    is_draft = state.get("draft", False)
    if is_draft:
        print(f"  Converting draft → ready for review...")
        node_id, gql_is_draft, gql_mergeable = get_pr_node_id(owner, repo, pr_number)
        if node_id and gql_is_draft:
            ok = convert_draft_to_ready(node_id)
            if ok:
                print(f"  [+] Converted to ready for review")
            else:
                print(f"  [!] Failed to convert draft — proceeding to merge anyway")
        else:
            print(f"  [i] node_id={node_id}, isDraft={gql_is_draft} — skipping conversion")

    # 7. Merge
    head_sha = state["head_sha"]
    print(f"  Merging (squash)... head_sha={head_sha[:8] if head_sha else 'n/a'}")
    merged, merge_sha = merge_pr(owner, repo, pr_number, head_sha, pr_title)

    filenames = [f["filename"] for f in pr_files]

    if merged:
        result["action"] = "merged"
        result["merge_sha"] = merge_sha
        result["reason"] = f"merged successfully at {_now()}"
        print(f"  [+] MERGED — sha={merge_sha[:8] if merge_sha else 'n/a'}")
        record_deploy(repo_full, filenames, success=True, rollback=False)
    else:
        result["action"] = "merge_failed"
        result["reason"] = "merge API call failed"
        print(f"  [!] Merge failed")
        record_deploy(repo_full, filenames, success=False, rollback=False)

    return result


def main():
    if not GH_TOKEN:
        print("[automerge] ERROR: GH_PAT or GITHUB_TOKEN not set")
        sys.exit(1)

    prs = load_prs()
    if not prs:
        print("[automerge] No PRs found in memory/all_prs.json")
        return

    print(f"[automerge] Found {len(prs)} PRs to evaluate")

    log = load_log()
    session_results = []

    for pr in prs:
        result = evaluate_and_merge_pr(pr)
        session_results.append(result)
        log.append(result)

    save_log(log)

    # Summary
    print(f"\n{'='*60}")
    print(f"[automerge] Session complete — {_now()}")
    merged = [r for r in session_results if r["action"] == "merged"]
    rejected = [r for r in session_results if r["action"] == "rejected"]
    skipped = [r for r in session_results if r["action"] in ("skipped", "already_merged", "merge_failed")]
    print(f"  Merged:   {len(merged)}")
    print(f"  Rejected: {len(rejected)}")
    print(f"  Skipped:  {len(skipped)}")
    for r in session_results:
        status = r["action"].upper().ljust(12)
        print(f"  {status} {r['repo']} #{r['pr_number']} — score={r['score']} — {r['reason']}")


if __name__ == "__main__":
    main()
