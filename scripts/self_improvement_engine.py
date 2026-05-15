"""
MIFTEH OS — Self-Improvement Engine
Analyzes MIFTEH OS itself: token efficiency, cost-per-feature, workflow health,
prompt quality, and generation velocity. Calls OpenAI for recommendations and
saves a report to memory/self_improvement_report.json.

Optionally creates a GitHub Issue summarizing the top improvement opportunities.
"""
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, today_str

GH_TOKEN  = os.environ.get("GH_PAT") or os.environ.get("GITHUB_TOKEN", "")
SELF_REPO = "Zakoosh/MIFTEH-AI-OS"
MEMORY    = Path("memory")
OUTPUTS   = Path("outputs")
WORKFLOWS = Path(".github/workflows")


# ── data collectors ───────────────────────────────────────────────────────────

def collect_output_metrics() -> dict:
    """Aggregate cost, token, and velocity metrics from all output records."""
    records = []
    for proj_dir in OUTPUTS.iterdir():
        if not proj_dir.is_dir() or proj_dir.name.startswith("."):
            continue
        for type_dir in proj_dir.iterdir():
            if not type_dir.is_dir():
                continue
            for f in type_dir.glob("*.json"):
                if f.name == "latest.json":
                    continue
                try:
                    records.append(json.loads(f.read_text()))
                except Exception:
                    pass

    if not records:
        return {"total": 0}

    records.sort(key=lambda x: x.get("generated_at", ""), reverse=True)

    total_tokens = sum(r.get("tokens_used", 0) for r in records)
    total_cost   = sum(r.get("cost_usd", 0.0) for r in records)
    ai_records   = [r for r in records if r.get("ai_generated")]
    n = len(records)
    n_ai = len(ai_records)

    # velocity: records in last 7 days
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    recent = []
    for r in records:
        try:
            dt = datetime.fromisoformat(r.get("generated_at", "").replace("Z", "+00:00"))
            if dt >= cutoff:
                recent.append(r)
        except Exception:
            pass

    # by project
    by_project = {}
    for r in records:
        p = r.get("project", "unknown")
        entry = by_project.setdefault(p, {"count": 0, "tokens": 0, "cost": 0.0, "ai": 0})
        entry["count"] += 1
        entry["tokens"] += r.get("tokens_used", 0)
        entry["cost"] += r.get("cost_usd", 0.0)
        if r.get("ai_generated"):
            entry["ai"] += 1

    # by type
    by_type = {}
    for r in records:
        t = r.get("operation_type") or r.get("feature_type", "unknown")
        entry = by_type.setdefault(t, {"count": 0, "tokens": 0})
        entry["count"] += 1
        entry["tokens"] += r.get("tokens_used", 0)

    avg_tokens  = round(total_tokens / max(n_ai, 1))
    avg_cost    = round(total_cost / max(n_ai, 1), 6)
    token_eff   = round(n_ai / max(total_tokens / 1000, 0.001), 3)  # features per 1K tokens

    return {
        "total": n,
        "ai_generated": n_ai,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "avg_tokens_per_feature": avg_tokens,
        "avg_cost_per_feature_usd": avg_cost,
        "token_efficiency": token_eff,
        "features_last_7d": len(recent),
        "by_project": by_project,
        "by_type": by_type,
        "latest_records": [
            {
                "project": r.get("project"),
                "type": r.get("operation_type") or r.get("feature_type"),
                "tokens": r.get("tokens_used", 0),
                "cost": r.get("cost_usd", 0.0),
                "generated_at": r.get("generated_at"),
            }
            for r in records[:10]
        ],
    }


def collect_workflow_metrics() -> dict:
    """Inventory all GitHub Actions workflows and report their configuration."""
    workflows = []
    if WORKFLOWS.exists():
        for f in sorted(WORKFLOWS.glob("*.yml")):
            try:
                content = f.read_text()
                # extract cron schedules
                import re
                crons = re.findall(r"cron:\s*'([^']+)'", content)
                # detect key scripts used
                scripts = re.findall(r"python scripts/(\S+\.py)", content)
                workflows.append({
                    "file": f.name,
                    "schedules": crons,
                    "scripts": list(dict.fromkeys(scripts)),
                    "has_openai": "OPENAI_API_KEY" in content,
                    "has_gh_pat": "GH_PAT" in content,
                    "size_lines": len(content.splitlines()),
                })
            except Exception:
                pass
    return {
        "total": len(workflows),
        "workflows": workflows,
    }


def collect_qa_metrics() -> dict:
    """Load visual QA summary if available."""
    f = MEMORY / "visual_qa_summary.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def collect_trust_metrics() -> dict:
    f = MEMORY / "trust_scores.json"
    if f.exists():
        try:
            d = json.loads(f.read_text())
            repos = d.get("repos", {})
            cats  = d.get("categories", {})
            avg_repo = round(sum(repos.values()) / max(len(repos), 1))
            avg_cat  = round(sum(cats.values()) / max(len(cats), 1))
            return {
                "avg_repo_trust": avg_repo,
                "avg_category_trust": avg_cat,
                "suspended_repos": d.get("suspended_repos", []),
                "suspended_cats": d.get("suspended_categories", []),
                "repos": repos,
                "categories": cats,
            }
        except Exception:
            pass
    return {}


def collect_automerge_metrics() -> dict:
    f = MEMORY / "automerge_log.json"
    if not f.exists():
        return {}
    try:
        log = json.loads(f.read_text())
        merges    = [e for e in log if e.get("action") == "merged"]
        skips     = [e for e in log if e.get("action") == "skipped"]
        rollbacks = [e for e in log if e.get("action") == "rollback"]
        avg_score = round(
            sum(e.get("score", 0) for e in merges) / max(len(merges), 1)
        )
        return {
            "total_evaluated": len(log),
            "merged": len(merges),
            "skipped": len(skips),
            "rollbacks": len(rollbacks),
            "avg_merge_score": avg_score,
            "merge_rate_pct": round(len(merges) / max(len(log), 1) * 100),
        }
    except Exception:
        return {}


# ── AI analysis ───────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an AI systems analyst reviewing the internal performance of MIFTEH OS,
an autonomous AI operating system. You analyze operational metrics and return a JSON improvement report.
Be specific, actionable, and critical. Prioritize improvements by expected impact.
Return valid JSON only."""

def build_analysis_prompt(metrics: dict) -> str:
    return f"""Analyze MIFTEH OS's self-reported operational metrics and return a JSON improvement report.

METRICS SNAPSHOT:
{json.dumps(metrics, indent=2, ensure_ascii=False)[:4000]}

Return JSON with this exact structure:
{{
  "overall_health_score": <0-100 integer>,
  "health_summary": "<2-sentence summary of system health>",
  "efficiency_score": <0-100>,
  "quality_score": <0-100>,
  "velocity_score": <0-100>,
  "top_improvements": [
    {{
      "title": "<improvement title>",
      "category": "<token_efficiency|prompt_quality|workflow_health|qa_quality|cost_reduction|velocity>",
      "priority": "<high|medium|low>",
      "description": "<specific, actionable description>",
      "estimated_impact": "<what this would improve and by how much>",
      "effort": "<low|medium|high>"
    }}
  ],
  "token_analysis": {{
    "assessment": "<good|needs_improvement|critical>",
    "observation": "<specific observation about token usage patterns>",
    "recommendation": "<concrete recommendation>"
  }},
  "workflow_analysis": {{
    "assessment": "<good|needs_improvement|critical>",
    "observation": "<specific observation>",
    "recommendation": "<concrete recommendation>"
  }},
  "prompt_quality_notes": "<observations about prompt efficiency based on token counts>",
  "cost_projection": {{
    "current_monthly_usd": <estimated monthly cost at current rate>,
    "optimized_monthly_usd": <estimated after improvements>,
    "savings_pct": <percentage savings>
  }},
  "next_cycle_focus": "<one concrete focus for the next improvement cycle>"
}}

Return 5-8 improvements, ranked by priority and impact."""


# ── GitHub Issue creation ─────────────────────────────────────────────────────

def create_github_issue(report: dict) -> str | None:
    """Create a GitHub issue with the self-improvement report summary."""
    if not GH_TOKEN:
        return None

    top = report.get("top_improvements", [])[:3]
    body_lines = [
        f"## MIFTEH OS Self-Improvement Report — {today_str()}",
        "",
        f"**Overall Health**: {report.get('overall_health_score', '?')}/100",
        f"**Summary**: {report.get('health_summary', '')}",
        "",
        f"**Scores**: Efficiency {report.get('efficiency_score', '?')} | Quality {report.get('quality_score', '?')} | Velocity {report.get('velocity_score', '?')}",
        "",
        "## Top Improvements",
        "",
    ]
    for i, imp in enumerate(top, 1):
        body_lines += [
            f"### {i}. {imp.get('title', '')} `{imp.get('priority', '')}` `{imp.get('category', '')}`",
            f"{imp.get('description', '')}",
            f"**Impact**: {imp.get('estimated_impact', '')}",
            f"**Effort**: {imp.get('effort', '')}",
            "",
        ]

    proj = report.get("cost_projection", {})
    if proj:
        body_lines += [
            "## Cost Projection",
            f"- Current: ~${proj.get('current_monthly_usd', 0):.2f}/mo",
            f"- Optimized: ~${proj.get('optimized_monthly_usd', 0):.2f}/mo",
            f"- Savings: {proj.get('savings_pct', 0)}%",
            "",
        ]

    body_lines += [
        "## Next Cycle Focus",
        report.get("next_cycle_focus", ""),
        "",
        "_Auto-generated by MIFTEH OS Self-Improvement Engine_",
    ]

    payload = json.dumps({
        "title": f"[AI] Self-Improvement Report — health={report.get('overall_health_score', '?')}/100 ({today_str()})",
        "body": "\n".join(body_lines),
        "labels": ["ai-generated", "self-improvement"],
    }).encode()

    owner, repo = SELF_REPO.split("/")
    url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Bearer {GH_TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read())
            issue_url = data.get("html_url", "")
            print(f"[self-improve] GitHub issue created: {issue_url}")
            return issue_url
    except urllib.error.HTTPError as e:
        print(f"[self-improve] Issue creation failed: {e.code} — {e.read().decode()[:200]}")
        return None


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("[self-improve] Collecting operational metrics...")

    output_metrics   = collect_output_metrics()
    workflow_metrics = collect_workflow_metrics()
    qa_metrics       = collect_qa_metrics()
    trust_metrics    = collect_trust_metrics()
    automerge_metrics = collect_automerge_metrics()

    metrics_bundle = {
        "generated_at": now_iso(),
        "outputs": output_metrics,
        "workflows": workflow_metrics,
        "visual_qa": qa_metrics,
        "trust": trust_metrics,
        "automerge": automerge_metrics,
    }

    print(f"[self-improve] {output_metrics.get('total', 0)} outputs, "
          f"{workflow_metrics.get('total', 0)} workflows, "
          f"avg_tokens/feature={output_metrics.get('avg_tokens_per_feature', 0)}")

    print("[self-improve] Calling AI for improvement analysis...")
    sys_prompt  = SYSTEM_PROMPT
    user_prompt = build_analysis_prompt(metrics_bundle)

    ai_report, tokens, cost, ok = generate_json(sys_prompt, user_prompt, max_tokens=2500)

    if not ok or not ai_report:
        print("[self-improve] AI call failed — saving metrics only")
        ai_report = {
            "overall_health_score": 0,
            "health_summary": "AI analysis unavailable",
            "top_improvements": [],
        }

    report = {
        "generated_at": now_iso(),
        "tokens_used": tokens,
        "cost_usd": cost,
        "ai_generated": ok,
        "raw_metrics": metrics_bundle,
        **ai_report,
    }

    MEMORY.mkdir(parents=True, exist_ok=True)
    out = MEMORY / "self_improvement_report.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[self-improve] Report saved → {out}")
    print(f"[self-improve] Health score: {report.get('overall_health_score', '?')}/100")

    if report.get("top_improvements"):
        print("[self-improve] Top improvements:")
        for i, imp in enumerate(report["top_improvements"][:3], 1):
            print(f"  {i}. [{imp.get('priority','?').upper()}] {imp.get('title','')}")

    # Create GitHub issue if CREATE_ISSUE env var is set
    if os.environ.get("CREATE_GITHUB_ISSUE", "").lower() in ("1", "true", "yes") and ok:
        create_github_issue(report)

    return report


if __name__ == "__main__":
    main()
