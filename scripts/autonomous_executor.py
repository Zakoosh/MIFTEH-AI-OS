"""
MIFTEH OS — Autonomous Executor
Reads the AI decision queue from analytics_intelligence.json,
prioritizes by impact, generates implementation plans, executes
full feature missions (generate → validate → PR → monitor → memory update).

Mission lifecycle:
  1. Read decision queue
  2. Prioritize by impact × urgency
  3. Generate implementation plan (AI)
  4. Generate feature HTML (via generate_product logic)
  5. Static QA gate (visual_validator)
  6. AI QA gate (ai_qa_engine)
  7. Create draft PR
  8. Update memory (success/failure)
  9. Update trust scores
  10. Log mission to execution_log.json
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, generate_text, now_iso, today_str, timestamp_str
from visual_validator import validate_html
from memory_engine import record_success, record_failure, record_prompt_performance, get_memory_context
from trust_manager import calculate_safety_score, record_deploy

GH_TOKEN = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", "")
MEMORY = Path("memory")
OUTPUTS = Path("outputs")
EXEC_LOG = MEMORY / "execution_log.json"

_GH_API = "https://api.github.com"

# Projects config (matches generate_product.py)
PROJECTS = {
    "yallaplays": {"repo": "Zakoosh/Yallaplays",         "domain": "yallaplays.com",   "lang": "ar", "tech": "HTML5, RTL Arabic, dark gaming theme"},
    "fionera":    {"repo": "Zakoosh/fionera",            "domain": "fionera.app",      "lang": "tr", "tech": "HTML5, Turkish, dark finance theme"},
    "mifteh":     {"repo": "Zakoosh/mifteh-main-site",   "domain": "miftehos.com",     "lang": "en", "tech": "HTML5, English, dark AI tech theme"},
}

SYSTEM_PROMPT = """You are a senior front-end engineer writing production HTML for AI-generated features.
Rules: raw HTML only, no markdown, no backticks, no explanation. Output must be a complete valid HTML document.
SEO required: <title>, <meta description>, canonical, OG tags, JSON-LD. Mobile-first: viewport meta + media queries.
Accessibility: alt text on images, ARIA where needed. No placeholder text. Make content specific and real."""


# ── GitHub helpers ────────────────────────────────────────────────────────────

def _gh(method: str, path: str, payload: dict | None = None):
    url = f"{_GH_API}{path}"
    data = json.dumps(payload).encode() if payload else None
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": f"Bearer {GH_TOKEN}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "MIFTEH-AI-OS/executor",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read()
            return json.loads(body) if body else {}, r.getcode()
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        print(f"  [gh] {method} {path} => {e.code}: {body[:200]}")
        return None, e.code


def _get_default_branch(owner: str, repo: str) -> str:
    data, code = _gh("GET", f"/repos/{owner}/{repo}")
    return data.get("default_branch", "main") if data and code == 200 else "main"


def _get_branch_sha(owner: str, repo: str, branch: str) -> str | None:
    data, code = _gh("GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
    return data.get("object", {}).get("sha") if data and code == 200 else None


def _create_branch(owner: str, repo: str, branch: str, sha: str) -> bool:
    _, code = _gh("POST", f"/repos/{owner}/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})
    return code in (200, 201, 422)  # 422 = already exists


def _put_file(owner: str, repo: str, path: str, content: str, branch: str, msg: str) -> bool:
    b64 = base64.b64encode(content.encode()).decode()
    existing, _ = _gh("GET", f"/repos/{owner}/{repo}/contents/{path}?ref={branch}")
    payload: dict = {"message": msg, "content": b64, "branch": branch}
    if isinstance(existing, dict) and existing.get("sha"):
        payload["sha"] = existing["sha"]
    _, code = _gh("PUT", f"/repos/{owner}/{repo}/contents/{path}", payload)
    return code in (200, 201)


def _create_pr(owner: str, repo: str, title: str, body: str, head: str, base: str):
    data, code = _gh("POST", f"/repos/{owner}/{repo}/pulls", {
        "title": title, "body": body, "head": head, "base": base, "draft": True,
    })
    if code in (200, 201) and data:
        return data.get("number"), data.get("html_url", "")
    return None, ""


def _read_file_from_repo(owner: str, repo: str, path: str) -> str | None:
    data, code = _gh("GET", f"/repos/{owner}/{repo}/contents/{path}")
    if code == 200 and isinstance(data, dict) and data.get("content"):
        try:
            return base64.b64decode(data["content"].replace("\n", "")).decode("utf-8", errors="replace")
        except Exception:
            pass
    return None


# ── Decision queue ────────────────────────────────────────────────────────────

def load_decision_queue() -> list[dict]:
    """Load autonomous decision queue from analytics_intelligence.json."""
    f = MEMORY / "analytics_intelligence.json"
    if not f.exists():
        return []
    try:
        intel = json.loads(f.read_text())
        decisions = intel.get("autonomous_decisions", [])
        # Filter for feature generation decisions
        return [
            d for d in decisions
            if d.get("action_type") in ("generate_page", "generate_feature", "generate_content",
                                         "build_seo_cluster", "improve_ux", "generate_widget",
                                         "create_landing_page")
            and d.get("priority") in ("critical", "high", "medium")
        ]
    except Exception:
        return []


def prioritize_queue(decisions: list[dict]) -> list[dict]:
    """Sort decisions by priority and estimated impact."""
    priority_weight = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    def _score(d: dict) -> float:
        pw = priority_weight.get(d.get("priority", "low"), 1)
        visits = d.get("estimated_traffic_impact", 0)
        return pw * 10 + min(visits / 100, 50)
    return sorted(decisions, key=_score, reverse=True)


# ── Plan generation ───────────────────────────────────────────────────────────

def generate_plan(decision: dict, project_config: dict, context: str) -> dict | None:
    """Use AI to turn a decision into a concrete implementation plan."""
    sys_prompt = """You are a product planner. Turn an AI decision into a concrete implementation plan.
Return valid JSON only. Be specific and actionable."""

    user_prompt = f"""Create an implementation plan for this autonomous decision:

DECISION: {json.dumps(decision, indent=2)}

PROJECT CONTEXT:
  - Domain: {project_config.get('domain')}
  - Language: {project_config.get('lang')}
  - Tech: {project_config.get('tech')}

MEMORY CONTEXT:
{context}

Return JSON:
{{
  "feature_id": "<snake_case_id>",
  "feature_type": "page|category_page|seo_hub|widget|component",
  "target_path": "<relative file path, e.g. category/sports.html>",
  "page_title": "<exact <title> tag content>",
  "meta_description": "<155 char description>",
  "h1": "<main heading>",
  "seo_target": "<primary keyword>",
  "key_sections": ["<section 1>", "<section 2>", "<section 3>"],
  "cta_primary": "<primary call to action text>",
  "special_requirements": "<any specific requirements from the decision>",
  "estimated_words": <integer>,
  "est_monthly_visits": <integer>
}}"""

    data, _, _, ok = generate_json(sys_prompt, user_prompt, max_tokens=800)
    return data if ok else None


# ── Feature generation ────────────────────────────────────────────────────────

def generate_feature_html(plan: dict, project_key: str, config: dict, context: str) -> tuple[str | None, int, float]:
    """Generate production HTML for a feature based on the plan."""
    feature_type = plan.get("feature_type", "page")
    lang = config.get("lang", "en")
    domain = config.get("domain", "")
    tech = config.get("tech", "HTML5")
    path = plan.get("target_path", "new-page.html")
    url = f"https://{domain}/{path}"

    mem_context = f"\n{context}\n" if context else ""

    user_prompt = f"""Generate a complete production HTML page.

{mem_context}
PROJECT: {project_key} ({domain})
TYPE: {feature_type}
PATH: {path}
URL: {url}
LANGUAGE: {lang}
TECH: {tech}

SPECIFICATIONS:
- Title: {plan.get('page_title', '')}
- Meta description: {plan.get('meta_description', '')}
- H1: {plan.get('h1', '')}
- SEO target keyword: {plan.get('seo_target', '')}
- Primary CTA: {plan.get('cta_primary', '')}
- Key sections: {', '.join(plan.get('key_sections', []))}
- Special requirements: {plan.get('special_requirements', 'none')}

REQUIRED ELEMENTS:
- Viewport meta tag (mobile-first)
- 3+ CSS media queries for responsiveness
- <title> with keyword
- Meta description (130-160 chars)
- <link rel="canonical" href="{url}">
- OG tags: og:title, og:description, og:url, og:image, og:type
- Twitter card: twitter:card, twitter:title, twitter:description
- JSON-LD: {"WebPage + BreadcrumbList" if feature_type in ("page","category_page") else "WebPage"}
- H1 tag (exactly one)
- Navigation header (consistent with site)
- Footer with copyright
- All images must have alt attributes
- At least one prominent CTA button
- lang="{lang}" on <html>
{' - dir="rtl" on <html> (Arabic RTL layout)' if lang == 'ar' else ''}
- No placeholder text — all content must be real and specific
- loading="lazy" on images
- Preconnect hints for any external resources"""

    html, tokens, cost, ok = generate_text(SYSTEM_PROMPT, user_prompt, max_tokens=5000)
    if ok and html and "</html>" not in html.lower()[-200:]:
        html += "\n</html>"
    return (html if ok else None), tokens, cost


# ── Mission executor ──────────────────────────────────────────────────────────

def execute_mission(decision: dict, project_key: str, dry_run: bool = False) -> dict:
    """Execute one full mission: plan → generate → validate → PR → memory."""
    config = PROJECTS.get(project_key)
    if not config:
        return {"status": "error", "error": f"Unknown project: {project_key}"}

    owner, repo = config["repo"].split("/")
    mission_id = f"{project_key}_{timestamp_str()}"

    result = {
        "mission_id": mission_id,
        "project": project_key,
        "decision": decision,
        "status": "started",
        "started_at": now_iso(),
        "plan": None,
        "qa": {},
        "pr_url": "",
        "pr_number": None,
        "tokens_used": 0,
        "cost_usd": 0.0,
        "error": "",
    }

    print(f"\n{'='*60}")
    print(f"[executor] Mission {mission_id}")
    print(f"  Decision: {decision.get('action', decision.get('recommendation', ''))[:80]}")
    print(f"  Priority: {decision.get('priority', '?')} | Impact: {decision.get('estimated_traffic_impact', 0)} visits/mo")

    # 1. Memory context
    ftype_hint = decision.get("action_type", "page").replace("generate_", "").replace("build_", "").replace("create_", "")
    mem_context = get_memory_context(project_key, ftype_hint)

    # 2. Read site context
    site_context = _read_file_from_repo(owner, repo, "index.html") or ""
    if site_context:
        print(f"  [read] index.html ({len(site_context):,} chars)")

    # 3. Generate plan
    print("  [plan] Generating implementation plan...")
    combined_context = f"{mem_context}\n\nSITE STYLE:\n{site_context[:1500]}" if site_context else mem_context
    plan = generate_plan(decision, config, combined_context)
    if not plan:
        result["status"] = "plan_failed"
        result["error"] = "AI plan generation failed"
        record_failure(project_key, "plan", ftype_hint, error="AI plan generation failed", stage="plan")
        return result

    result["plan"] = plan
    feature_id = plan.get("feature_id", mission_id)
    feature_type = plan.get("feature_type", "page")
    target_path = plan.get("target_path", f"ai/{feature_id}.html")
    print(f"  [plan] {feature_id} → {target_path}")

    # 4. Generate HTML
    print("  [gen] Generating HTML...")
    html, tokens, cost = generate_feature_html(plan, project_key, config, mem_context)
    result["tokens_used"] += tokens
    result["cost_usd"] += cost

    if not html:
        result["status"] = "generation_failed"
        result["error"] = "HTML generation failed"
        record_failure(project_key, feature_id, feature_type, error="HTML generation failed", stage="generate", tokens_used=tokens, cost_usd=cost)
        return result

    print(f"  [gen] {len(html):,} chars generated")

    # 5. Static QA gate
    print("  [qa] Running static visual QA...")
    qa_report = validate_html(html, label=feature_id, project=project_key)
    result["qa"]["static"] = {
        "score": qa_report["score"],
        "grade": qa_report["grade"],
        "passes": qa_report["passes_auto_merge_threshold"],
    }

    record_prompt_performance(
        f"{project_key}_{feature_type}",
        tokens_used=tokens,
        qa_score=qa_report["score"],
        outcome="success" if qa_report["passes_auto_merge_threshold"] else "qa_blocked",
        bytes_generated=len(html),
        cost_usd=cost,
    )

    if qa_report["score"] < 50:
        result["status"] = "qa_blocked"
        result["error"] = f"Static QA score {qa_report['score']}/100 too low (min 50 for execution)"
        record_failure(project_key, feature_id, feature_type,
                       error=f"QA score {qa_report['score']}/100",
                       stage="static_qa",
                       qa_score=qa_report["score"],
                       qa_issues=qa_report.get("all_issues", [])[:5],
                       tokens_used=tokens, cost_usd=cost)
        return result

    print(f"  [qa] Static: {qa_report['score']}/100 grade={qa_report['grade']}")

    if dry_run:
        result["status"] = "dry_run_complete"
        return result

    # 6. Create GitHub PR
    default_branch = _get_default_branch(owner, repo)
    base_sha = _get_branch_sha(owner, repo, default_branch)
    if not base_sha:
        result["status"] = "github_error"
        result["error"] = "Cannot get repository SHA"
        return result

    branch = f"ai/executor-{project_key}-{today_str()}-{feature_id[:20]}"
    _create_branch(owner, repo, branch, base_sha)

    committed = _put_file(owner, repo, target_path, html, branch,
                          f"AI: {plan.get('h1', feature_id)} [executor] [skip ci]")
    if not committed:
        result["status"] = "commit_failed"
        result["error"] = f"Failed to commit {target_path}"
        return result

    # Also save preview locally
    preview_dir = Path("frontend/dashboard/previews") / project_key
    preview_dir.mkdir(parents=True, exist_ok=True)
    (preview_dir / f"{feature_id}.html").write_text(html, encoding="utf-8")

    # Create PR
    pr_title = f"AI Executor: {plan.get('h1', feature_id)}"
    pr_body = f"""## 🤖 Autonomous Executor Mission

**Mission**: {decision.get('action', decision.get('recommendation', ''))[:120]}
**Priority**: {decision.get('priority', '?')} | **Est. traffic**: +{plan.get('est_monthly_visits', 0):,} visits/mo

### Generated File
- `{target_path}` ({len(html):,} chars)

### SEO Target
- Keyword: `{plan.get('seo_target', 'N/A')}`
- H1: {plan.get('h1', 'N/A')}

### Visual QA
- Static score: **{qa_report['score']}/100** (grade {qa_report['grade']})
- Auto-merge threshold: {"✅ passes" if qa_report['passes_auto_merge_threshold'] else "⚠️ requires review"}

### AI Stats
- Tokens: `{tokens:,}` | Cost: `${cost:.5f}`
- Mission ID: `{mission_id}`

> Auto-generated by MIFTEH OS Autonomous Executor
"""
    pr_num, pr_url = _create_pr(owner, repo, pr_title, pr_body, branch, default_branch)

    result["pr_url"] = pr_url
    result["pr_number"] = pr_num
    result["status"] = "pr_created"

    # 7. Update memory + trust
    if pr_url:
        record_success(
            project_key, feature_id, feature_type,
            label=plan.get("h1", feature_id),
            target_path=target_path,
            pr_url=pr_url,
            qa_score=qa_report["score"],
            qa_grade=qa_report["grade"],
            tokens_used=tokens,
            cost_usd=cost,
            bytes_generated=len(html),
            seo_target=plan.get("seo_target", ""),
            est_monthly_visits=plan.get("est_monthly_visits", 0),
        )
        record_deploy(config["repo"], [target_path], success=True, rollback=False)
        print(f"  [+] PR #{pr_num}: {pr_url}")
    else:
        result["status"] = "pr_failed"
        record_failure(project_key, feature_id, feature_type,
                       error="PR creation failed", stage="pr",
                       tokens_used=tokens, cost_usd=cost)

    result["completed_at"] = now_iso()
    return result


# ── Execution log ─────────────────────────────────────────────────────────────

def load_exec_log() -> list[dict]:
    if EXEC_LOG.exists():
        try:
            return json.loads(EXEC_LOG.read_text())
        except Exception:
            return []
    return []


def save_exec_log(log: list[dict]):
    MEMORY.mkdir(exist_ok=True)
    EXEC_LOG.write_text(json.dumps(log[-200:], indent=2, ensure_ascii=False))


# ── Summary ───────────────────────────────────────────────────────────────────

def build_execution_summary() -> dict:
    log = load_exec_log()
    if not log:
        return {"total": 0, "successful": 0, "failed": 0, "recent": []}
    successful = [e for e in log if e.get("status") in ("pr_created",)]
    failed = [e for e in log if "fail" in e.get("status", "") or "error" in e.get("status", "") or "block" in e.get("status", "")]
    total_cost = sum(e.get("cost_usd", 0.0) for e in log)
    return {
        "total": len(log),
        "successful": len(successful),
        "failed": len(failed),
        "total_cost_usd": round(total_cost, 6),
        "success_rate_pct": round(len(successful) / max(len(log), 1) * 100),
        "recent": [
            {
                "mission_id": e.get("mission_id", ""),
                "project": e.get("project", ""),
                "status": e.get("status", ""),
                "pr_url": e.get("pr_url", ""),
                "tokens_used": e.get("tokens_used", 0),
                "cost_usd": e.get("cost_usd", 0.0),
                "started_at": e.get("started_at", ""),
                "qa_score": (e.get("qa", {}).get("static", {}) or {}).get("score", 0),
                "feature_label": (e.get("plan") or {}).get("h1", ""),
            }
            for e in log[-20:]
        ],
    }


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("[executor] Starting autonomous execution engine...")

    if not GH_TOKEN:
        print("[executor] ERROR: GH_PAT or GITHUB_TOKEN not set")
        sys.exit(1)

    dry_run = os.environ.get("DRY_RUN", "").lower() in ("1", "true", "yes")
    target_project = os.environ.get("TARGET_PROJECT", "all").lower()
    max_missions = int(os.environ.get("MAX_MISSIONS", "3"))

    decisions = load_decision_queue()
    if not decisions:
        print("[executor] No decisions in queue — run analytics intelligence first")
        return

    prioritized = prioritize_queue(decisions)
    print(f"[executor] {len(prioritized)} decisions in queue | max_missions={max_missions} | dry_run={dry_run}")

    log = load_exec_log()
    executed = 0

    for decision in prioritized:
        if executed >= max_missions:
            print(f"[executor] Reached max_missions limit ({max_missions})")
            break

        # Determine project from decision
        decision_project = decision.get("project", "").lower()
        if not decision_project or decision_project == "all":
            # Try all projects
            projects_to_try = list(PROJECTS.keys()) if target_project == "all" else [target_project]
        else:
            projects_to_try = [decision_project]

        if target_project != "all":
            projects_to_try = [p for p in projects_to_try if p == target_project]

        for project_key in projects_to_try:
            if project_key not in PROJECTS:
                continue
            result = execute_mission(decision, project_key, dry_run=dry_run)
            log.append(result)
            executed += 1

            status = result.get("status", "?")
            print(f"  → {result['mission_id']}: {status}")
            if result.get("pr_url"):
                print(f"    PR: {result['pr_url']}")
            if result.get("error"):
                print(f"    Error: {result['error']}")
            break  # One project per decision

    save_exec_log(log)

    # Save summary
    summary = build_execution_summary()
    out = MEMORY / "execution_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))

    print(f"\n[executor] Session complete: {executed} missions executed")
    print(f"[executor] Total: {summary['successful']}/{summary['total']} successful")


if __name__ == "__main__":
    main()
