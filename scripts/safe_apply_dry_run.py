"""
Dry-run mode for safe-apply: reads repo files and runs AI analysis without committing.
Called by ai-safe-apply.yml when DRY_RUN=true.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from analyze_repo_and_create_pr import build_files_context, get_default_branch, analyze_and_improve

REPOS = {
    "yallaplays": ("Zakoosh/Yallaplays", "yallaplays.com"),
    "fionera": ("Zakoosh/fionera", "fionera.app"),
    "mifteh": ("Zakoosh/mifteh-main-site", "miftehos.com"),
}

target = os.environ.get("TARGET_REPO", "yallaplays")
repo_full, domain = REPOS.get(target, ("Zakoosh/Yallaplays", "yallaplays.com"))
owner, repo = repo_full.split("/")

branch = get_default_branch(owner, repo)
ctx, files = build_files_context(owner, repo, ["index.html", "robots.txt", "sitemap.xml"], branch)
print(f"[dry-run] Read {len(files)} file(s): {list(files.keys())}")

data, tokens, cost, ok = analyze_and_improve(target, domain, "web", ctx)
if ok:
    issues = (data or {}).get("analysis", {}).get("issues_found", [])
    print(f"[dry-run] Found {len(issues)} issues, {tokens} tokens, ${cost:.4f}")
    for issue in issues:
        print(f"  - {issue}")
else:
    print("[dry-run] Analysis failed")
    sys.exit(1)
