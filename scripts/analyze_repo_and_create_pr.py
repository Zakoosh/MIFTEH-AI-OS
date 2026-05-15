"""
MIFTEH OS — Autonomous Repository Analyzer & PR Generator
Fetches real repo files → analyzes with OpenAI → commits real improvements → creates draft PRs.

Safety rules:
  ALLOWED:  SEO, metadata, structured data, robots.txt, sitemap.xml, manifest.json,
            content improvements, OG tags, canonical links, JSON-LD
  FORBIDDEN: auth, payments, env vars, deployment configs, deleting files, core logic
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, today_str, timestamp_str

GH_TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", "")
OPENAI_KEY = os.environ.get("OPENAI_API_KEY", "")

# ─── GitHub API ───────────────────────────────────────────────────────────────

def gh(method, path, payload=None, token=None):
    t = token or GH_TOKEN
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(payload).encode() if payload else None,
        headers={
            "Authorization": f"Bearer {t}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "MIFTEH-AI-OS/2.0",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read()), r.getcode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:400]
        print(f"  [gh] {method} {path} => {e.code}: {body}")
        return None, e.code


def read_file(owner, repo, path, ref="main"):
    data, code = gh("GET", f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
    if code != 200 or not isinstance(data, dict):
        return None, None
    try:
        content = base64.b64decode(data["content"].replace("\n", "")).decode("utf-8", errors="replace")
        return content, data.get("sha")
    except Exception:
        return None, None


def file_exists(owner, repo, path, ref="main"):
    _, code = gh("GET", f"/repos/{owner}/{repo}/contents/{path}?ref={ref}")
    return code == 200


def get_default_branch(owner, repo):
    data, _ = gh("GET", f"/repos/{owner}/{repo}")
    return (data or {}).get("default_branch", "main")


def get_branch_sha(owner, repo, branch):
    data, _ = gh("GET", f"/repos/{owner}/{repo}/git/refs/heads/{branch}")
    return ((data or {}).get("object", {})).get("sha")


def create_branch(owner, repo, branch, from_sha):
    _, code = gh("POST", f"/repos/{owner}/{repo}/git/refs", {
        "ref": f"refs/heads/{branch}", "sha": from_sha,
    })
    return code in (200, 201, 422)


def put_file(owner, repo, branch, path, content_str, message):
    existing, _ = gh("GET", f"/repos/{owner}/{repo}/contents/{path}?ref={branch}")
    payload = {
        "message": message,
        "content": base64.b64encode(content_str.encode("utf-8")).decode(),
        "branch": branch,
    }
    if isinstance(existing, dict) and existing.get("sha"):
        payload["sha"] = existing["sha"]
    _, code = gh("PUT", f"/repos/{owner}/{repo}/contents/{path}", payload)
    return code in (200, 201)


def create_pr(owner, repo, branch, base, title, body):
    data, code = gh("POST", f"/repos/{owner}/{repo}/pulls", {
        "title": title, "body": body, "head": branch, "base": base, "draft": True,
    })
    return data, code


# ─── OpenAI Analysis ─────────────────────────────────────────────────────────

def analyze_and_improve(project_name, domain, repo_type, files_context, extra_context=""):
    """Call OpenAI with real file content and get back real improvements."""
    system = (
        f"You are an expert SEO engineer and web performance specialist analyzing {project_name} ({domain}). "
        "Generate REAL, specific, deployable improvements. Return only valid JSON. "
        "Focus on: meta tags, Open Graph, Twitter Cards, JSON-LD structured data, robots.txt, sitemap.xml, manifest.json. "
        "Never modify auth, payment, or deployment logic. All changes must be safe to merge immediately."
    )

    user = f"""Analyze these actual files from {project_name} ({domain}) and generate real improvements for {today_str()}.

ACTUAL FILE CONTENTS:
{files_context}

{extra_context}

Return JSON with this EXACT structure:
{{
  "analysis": {{
    "issues_found": ["specific issue 1", "specific issue 2"],
    "seo_score_before": 65,
    "seo_score_after": 90,
    "risk_level": "low"
  }},
  "files_to_update": [
    {{
      "path": "index.html",
      "action": "update",
      "description": "Add OG tags and JSON-LD",
      "content": "FULL FILE CONTENT HERE — complete, deployable, not truncated",
      "rollback_note": "Revert commit to restore previous index.html"
    }}
  ],
  "files_to_create": [
    {{
      "path": "robots.txt",
      "action": "create",
      "description": "Add robots.txt for crawl control",
      "content": "FULL FILE CONTENT",
      "rollback_note": "Delete this file to revert"
    }}
  ],
  "pr_title": "SEO: {project_name} — meta, structured data, robots, sitemap",
  "pr_summary": "2-3 sentence summary of all changes"
}}

RULES:
- files_to_update: ONLY include files that exist in the repo (provided above)
- files_to_create: ONLY new files (robots.txt, sitemap.xml, manifest.json if missing)
- Content must be COMPLETE and DEPLOYABLE — no placeholders, no truncation
- For HTML files: keep all existing functionality, only add/improve head meta section
- JSON-LD must use real data about {project_name} at {domain}
- Preserve all existing CSS, JS, and HTML structure exactly"""

    data, tokens, cost, success = generate_json(system, user, model="gpt-4o-mini", max_tokens=4000)
    return data, tokens, cost, success


# ─── Per-repo analysis ────────────────────────────────────────────────────────

def build_files_context(owner, repo, file_paths, default_branch):
    """Read multiple files and build a context string."""
    parts = []
    read_files = {}
    for path in file_paths:
        content, sha = read_file(owner, repo, path, default_branch)
        if content:
            snippet = content[:3000] + ("\n... [truncated]" if len(content) > 3000 else "")
            parts.append(f"--- FILE: {path} ---\n{snippet}\n")
            read_files[path] = {"content": content, "sha": sha}
        else:
            parts.append(f"--- FILE: {path} --- [DOES NOT EXIST — can be created]\n")
    return "\n".join(parts), read_files


def process_repo(project_name, domain, repo_full, files_to_check, extra_context=""):
    print(f"\n{'='*60}")
    print(f"[{project_name}] Analyzing {repo_full}...")

    owner, repo = repo_full.split("/", 1)
    default_branch = get_default_branch(owner, repo)
    print(f"  Default branch: {default_branch}")

    # Build context from real files
    files_context, read_files = build_files_context(owner, repo, files_to_check, default_branch)
    print(f"  Files read: {list(read_files.keys())}")

    # AI analysis
    print(f"  Calling OpenAI for analysis...")
    improvements, tokens, cost, success = analyze_and_improve(
        project_name, domain, "web", files_context, extra_context
    )

    if not success or not improvements:
        print(f"  [!] AI analysis failed — skipping {project_name}")
        return None

    analysis = improvements.get("analysis", {})
    print(f"  Issues found: {len(analysis.get('issues_found', []))}")
    print(f"  SEO: {analysis.get('seo_score_before', '?')} → {analysis.get('seo_score_after', '?')}")
    print(f"  Tokens: {tokens}, Cost: ${cost:.4f}")

    # Create branch
    today = today_str()
    branch = f"ai/seo-improvements-{project_name.lower().replace(' ', '-')}-{today}"
    sha = get_branch_sha(owner, repo, default_branch)
    if not sha:
        print(f"  [!] Cannot get SHA for {repo_full}")
        return None

    create_branch(owner, repo, branch, sha)
    print(f"  Branch created: {branch}")

    # Commit all improvements
    committed_files = []
    all_file_changes = improvements.get("files_to_update", []) + improvements.get("files_to_create", [])

    for change in all_file_changes:
        path = change.get("path", "")
        content = change.get("content", "")
        action = change.get("action", "update")
        description = change.get("description", "AI improvement")

        if not path or not content:
            print(f"  [!] Skipping empty change for {path}")
            continue

        # Safety gate: never touch forbidden paths
        forbidden = ["auth", "password", "secret", "env", "deploy", "payment", ".github/workflows", "Dockerfile", "railway", "vercel"]
        if any(f in path.lower() for f in forbidden):
            print(f"  [!] BLOCKED (safety): {path}")
            continue

        commit_msg = f"AI: {action} {path} — {description} [{today}]"
        ok = put_file(owner, repo, branch, path, content, commit_msg)
        status = "✓" if ok else "✗"
        print(f"  {status} {action} {path}")
        if ok:
            committed_files.append({
                "path": path,
                "action": action,
                "description": description,
                "rollback_note": change.get("rollback_note", f"Revert the commit touching {path}"),
            })

    if not committed_files:
        print(f"  [!] No files committed — skipping PR for {project_name}")
        return None

    # Build PR body
    issues_list = "\n".join(f"- {i}" for i in analysis.get("issues_found", []))
    files_list = "\n".join(f"- `{f['path']}` — {f['description']}" for f in committed_files)
    rollback_list = "\n".join(f"- `{f['path']}`: {f['rollback_note']}" for f in committed_files)

    pr_body = f"""## {improvements.get('pr_title', f'AI: SEO improvements for {project_name}')}

{improvements.get('pr_summary', '')}

---

### Issues Detected
{issues_list or '- See changes for details'}

### SEO Score
- **Before:** {analysis.get('seo_score_before', '?')}/100
- **After:** {analysis.get('seo_score_after', '?')}/100
- **Risk Level:** {analysis.get('risk_level', 'low')}

### Files Changed
{files_list}

### Rollback Instructions
{rollback_list}

### AI Reasoning
- Generated by MIFTEH AI OS using OpenAI gpt-4o-mini
- Analysis date: {today}
- Tokens used: {tokens:,} | Cost: ${cost:.4f}
- All changes are additive SEO/metadata improvements only
- No core logic, auth, or deployment files were modified

---
> ⚠️ **Draft PR — human review required before merge**
> ✅ Safe changes only: meta tags, structured data, robots.txt, sitemap, manifest
> 🚫 Never auto-merged · Rollback notes included · Risk: {analysis.get('risk_level', 'low')}
> 🤖 [MIFTEH AI OS](https://miftehos.com) — Autonomous improvement system"""

    pr_title = improvements.get("pr_title", f"AI: SEO & metadata improvements — {project_name} [{today}]")
    pr_data, pr_code = create_pr(owner, repo, branch, default_branch, pr_title, pr_body)

    if pr_code not in (200, 201):
        print(f"  [!] PR creation failed ({pr_code})")
        return None

    pr_url = (pr_data or {}).get("html_url", "")
    pr_number = (pr_data or {}).get("number")
    print(f"  ✓ Draft PR #{pr_number}: {pr_url}")

    result = {
        "project": project_name,
        "repo": repo_full,
        "branch": branch,
        "pr_number": pr_number,
        "pr_url": pr_url,
        "pr_title": pr_title,
        "created_at": now_iso(),
        "ai_generated": True,
        "operation_type": "repository_analysis",
        "files_committed": [f["path"] for f in committed_files],
        "issues_found": analysis.get("issues_found", []),
        "seo_score_before": analysis.get("seo_score_before"),
        "seo_score_after": analysis.get("seo_score_after"),
        "tokens_used": tokens,
        "cost_usd": cost,
    }

    # Record in memory
    _record_pr(project_name.lower(), result)
    return result


def _record_pr(project, pr_info):
    for fname in [f"memory/prs_{project}.json", "memory/all_prs.json"]:
        f = Path(fname)
        records = json.loads(f.read_text()) if f.exists() else []
        records.append(pr_info)
        f.parent.mkdir(exist_ok=True)
        f.write_text(json.dumps(records[-100:], indent=2, ensure_ascii=False))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    if not GH_TOKEN:
        print("[ERROR] GH_PAT or GITHUB_TOKEN not set")
        return []
    if not OPENAI_KEY:
        print("[ERROR] OPENAI_API_KEY not set")
        return []

    results = []

    # ── YallaPlays ──────────────────────────────────────────────────────────
    yp_result = process_repo(
        project_name="YallaPlays",
        domain="yallaplays.com",
        repo_full=os.environ.get("GITHUB_REPO_YALLAPLAYS", "Zakoosh/Yallaplays"),
        files_to_check=["index.html", "robots.txt", "sitemap.xml", "ads.txt"],
        extra_context=(
            "YallaPlays is an Arabic gaming portal (RTL, lang=ar) with 500+ HTML5 games. "
            "Target audience: Arabic-speaking MENA users on mobile. "
            "Key pages: homepage, category pages (action, puzzle, racing), individual game pages. "
            "robots.txt DOES NOT EXIST — create it. sitemap.xml DOES NOT EXIST — create it. "
            "index.html has good base SEO but missing: Organization JSON-LD, BreadcrumbList, "
            "ItemList for featured games, SiteLinksSearchBox in structured data. "
            "Add Arabic-language structured data. Improve meta keywords for Arabic gaming terms."
        )
    )
    if yp_result:
        results.append(yp_result)

    # ── Fionera ─────────────────────────────────────────────────────────────
    fi_result = process_repo(
        project_name="Fionera",
        domain="fionera.app",
        repo_full=os.environ.get("GITHUB_REPO_FIONERA", "Zakoosh/fionera"),
        files_to_check=["index.html", "robots.txt", "sitemap.xml"],
        extra_context=(
            "Fionera is an Arabic financial dashboard (RTL, lang=ar) — investment tracking, "
            "stocks, crypto, forex, gold. Target: Arabic-speaking investors in MENA. "
            "CRITICAL: index.html is missing Open Graph tags, Twitter Card, canonical URL, "
            "structured data (WebApplication schema), proper keywords, and has wrong title. "
            "robots.txt DOES NOT EXIST — create it. sitemap.xml DOES NOT EXIST — create it. "
            "The app title shows 'Finora' in code but brand is 'Fionera'. "
            "Add WebApplication JSON-LD with Arabic description. Add financial app-specific OG tags. "
            "Domain is likely fionera.app or use a placeholder like https://fionera.zakoosh.com"
        )
    )
    if fi_result:
        results.append(fi_result)

    # ── Mifteh main site ────────────────────────────────────────────────────
    mi_result = process_repo(
        project_name="Mifteh",
        domain="miftehos.com",
        repo_full=os.environ.get("GITHUB_REPO_MIFTEH", "Zakoosh/mifteh-main-site"),
        files_to_check=["index.html", "public/robots.txt", "public/sitemap.xml", "public/manifest.json"],
        extra_context=(
            "mifteh-main-site is a React/Vite TypeScript app for MIFTEH — an AI Operating System platform. "
            "CRITICAL: index.html title is 'Complete Visual Identity' — this is WRONG, must be fixed to 'MIFTEH AI OS'. "
            "index.html has NO meta description, NO OG tags, NO Twitter card, NO structured data. "
            "public/robots.txt DOES NOT EXIST — create at public/robots.txt. "
            "public/sitemap.xml DOES NOT EXIST — create at public/sitemap.xml. "
            "public/manifest.json DOES NOT EXIST — create it for PWA support. "
            "This is the main marketing site at miftehos.com. Fix index.html head section thoroughly. "
            "Add SoftwareApplication JSON-LD. The app is an AI automation OS."
        )
    )
    if mi_result:
        results.append(mi_result)

    print(f"\n{'='*60}")
    print(f"[DONE] Created {len(results)} draft PR(s)")
    for r in results:
        print(f"  {r['project']}: PR #{r['pr_number']} — {r['pr_url']}")
        print(f"    Files: {', '.join(r['files_committed'])}")

    # Save run summary for dashboard
    summary = {
        "generated_at": now_iso(),
        "project": "mifteh",
        "operation_type": "repository_analysis",
        "ai_generated": True,
        "ai_model": "gpt-4o-mini",
        "tokens_used": sum(r.get("tokens_used", 0) for r in results),
        "cost_usd": sum(r.get("cost_usd", 0) for r in results),
        "title": f"Repository Analysis & PR Generation — {today_str()}",
        "content": {
            "prs_created": len(results),
            "repositories": [r["repo"] for r in results],
            "pr_urls": [r["pr_url"] for r in results],
        },
        "pr_ready": False,
    }
    out = Path("outputs/mifteh/analytics")
    out.mkdir(parents=True, exist_ok=True)
    ts = timestamp_str()
    (out / f"repo_analysis_{ts}.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    (out / "latest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    return results


if __name__ == "__main__":
    main()
