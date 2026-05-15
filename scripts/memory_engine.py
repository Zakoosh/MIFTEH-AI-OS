"""
MIFTEH OS — Memory Engine
Persistent learning system: records successes, failures, prompt performance,
SEO/UX strategies, and cross-project learnings. Feeds context back into
all AI generators so the system improves with every cycle.

Directory layout:
  memory/
    successes/   {project}_{feature_id}_{ts}.json
    failures/    {project}_{feature_id}_{ts}.json
    prompts/     {prompt_key}.json   (one file per prompt type)
    strategies/  {project}_{type}.json
    learnings/   {ts}_learnings.json
    memory_index.json  (fast lookup for dashboard)
"""
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso, timestamp_str

MEMORY = Path("memory")
MEM_SUCCESSES  = MEMORY / "successes"
MEM_FAILURES   = MEMORY / "failures"
MEM_PROMPTS    = MEMORY / "prompts"
MEM_STRATEGIES = MEMORY / "strategies"
MEM_LEARNINGS  = MEMORY / "learnings"
INDEX_FILE     = MEMORY / "memory_index.json"

for _d in (MEM_SUCCESSES, MEM_FAILURES, MEM_PROMPTS, MEM_STRATEGIES, MEM_LEARNINGS):
    _d.mkdir(parents=True, exist_ok=True)


# ── helpers ───────────────────────────────────────────────────────────────────

def _write(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def _read(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception:
        return None


def _load_all(directory: Path) -> list[dict]:
    records = []
    if not directory.exists():
        return records
    for f in sorted(directory.glob("*.json"), reverse=True):
        d = _read(f)
        if d:
            records.append(d)
    return records


# ── success / failure recording ───────────────────────────────────────────────

def record_success(
    project: str,
    feature_id: str,
    feature_type: str,
    *,
    label: str = "",
    target_path: str = "",
    pr_url: str = "",
    qa_score: int = 0,
    qa_grade: str = "",
    tokens_used: int = 0,
    cost_usd: float = 0.0,
    bytes_generated: int = 0,
    seo_target: str = "",
    est_monthly_visits: int = 0,
    extra: dict | None = None,
) -> dict:
    ts = timestamp_str()
    record = {
        "type": "success",
        "project": project,
        "feature_id": feature_id,
        "feature_type": feature_type,
        "label": label,
        "target_path": target_path,
        "pr_url": pr_url,
        "qa_score": qa_score,
        "qa_grade": qa_grade,
        "tokens_used": tokens_used,
        "cost_usd": cost_usd,
        "bytes_generated": bytes_generated,
        "seo_target": seo_target,
        "est_monthly_visits": est_monthly_visits,
        "recorded_at": now_iso(),
        **(extra or {}),
    }
    _write(MEM_SUCCESSES / f"{project}_{feature_id}_{ts}.json", record)
    _update_index(record)
    return record


def record_failure(
    project: str,
    feature_id: str,
    feature_type: str,
    *,
    error: str = "",
    stage: str = "",
    qa_score: int = 0,
    qa_issues: list | None = None,
    tokens_used: int = 0,
    cost_usd: float = 0.0,
    extra: dict | None = None,
) -> dict:
    ts = timestamp_str()
    record = {
        "type": "failure",
        "project": project,
        "feature_id": feature_id,
        "feature_type": feature_type,
        "error": error,
        "stage": stage,
        "qa_score": qa_score,
        "qa_issues": qa_issues or [],
        "tokens_used": tokens_used,
        "cost_usd": cost_usd,
        "recorded_at": now_iso(),
        **(extra or {}),
    }
    _write(MEM_FAILURES / f"{project}_{feature_id}_{ts}.json", record)
    _update_index(record)
    return record


# ── prompt performance ────────────────────────────────────────────────────────

def record_prompt_performance(
    prompt_key: str,
    *,
    tokens_used: int,
    qa_score: int,
    outcome: str,           # "success" | "qa_blocked" | "failed"
    bytes_generated: int = 0,
    cost_usd: float = 0.0,
):
    """Update rolling prompt performance for a given prompt key."""
    path = MEM_PROMPTS / f"{prompt_key}.json"
    rec = _read(path) or {
        "prompt_key": prompt_key,
        "runs": 0,
        "successes": 0,
        "qa_blocks": 0,
        "failures": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "avg_qa_score": 0,
        "avg_bytes": 0,
        "history": [],
    }

    rec["runs"] += 1
    rec["total_tokens"] += tokens_used
    rec["total_cost"] = round(rec["total_cost"] + cost_usd, 8)
    if outcome == "success":
        rec["successes"] += 1
    elif outcome == "qa_blocked":
        rec["qa_blocks"] += 1
    else:
        rec["failures"] += 1

    # Rolling average for QA score
    n = rec["runs"]
    rec["avg_qa_score"] = round((rec["avg_qa_score"] * (n - 1) + qa_score) / n)
    rec["avg_bytes"] = round((rec["avg_bytes"] * (n - 1) + bytes_generated) / n)

    rec["history"] = ([{
        "outcome": outcome,
        "qa_score": qa_score,
        "tokens": tokens_used,
        "cost": cost_usd,
        "ts": now_iso(),
    }] + rec["history"])[:30]

    rec["success_rate"] = round(rec["successes"] / max(rec["runs"], 1) * 100)
    rec["updated_at"] = now_iso()
    _write(path, rec)
    return rec


def get_prompt_stats(prompt_key: str) -> dict | None:
    return _read(MEM_PROMPTS / f"{prompt_key}.json")


def get_best_prompts(limit: int = 5) -> list[dict]:
    all_p = _load_all(MEM_PROMPTS)
    return sorted(
        [p for p in all_p if p.get("runs", 0) >= 2],
        key=lambda x: (x.get("avg_qa_score", 0), x.get("success_rate", 0)),
        reverse=True,
    )[:limit]


# ── strategy memory ───────────────────────────────────────────────────────────

def update_strategy(project: str, strategy_type: str, data: dict):
    """Persist a strategy record for a project/type pair."""
    path = MEM_STRATEGIES / f"{project}_{strategy_type}.json"
    existing = _read(path) or {}
    merged = {**existing, **data, "project": project, "strategy_type": strategy_type, "updated_at": now_iso()}
    _write(path, merged)
    return merged


def get_strategy(project: str, strategy_type: str) -> dict | None:
    return _read(MEM_STRATEGIES / f"{project}_{strategy_type}.json")


def get_all_strategies(project: str | None = None) -> list[dict]:
    all_s = _load_all(MEM_STRATEGIES)
    if project:
        return [s for s in all_s if s.get("project") == project]
    return all_s


# ── learnings ─────────────────────────────────────────────────────────────────

def save_learnings(learnings: dict):
    ts = timestamp_str()
    path = MEM_LEARNINGS / f"{ts}_learnings.json"
    _write(path, {**learnings, "generated_at": now_iso()})
    return path


def get_recent_learnings(limit: int = 3) -> list[dict]:
    return _load_all(MEM_LEARNINGS)[:limit]


# ── memory index ──────────────────────────────────────────────────────────────

def _update_index(record: dict):
    index = _read(INDEX_FILE) or {
        "total_successes": 0,
        "total_failures": 0,
        "by_project": {},
        "by_type": {},
        "recent": [],
        "updated_at": "",
    }

    t = record.get("type", "success")
    if t == "success":
        index["total_successes"] = index.get("total_successes", 0) + 1
    else:
        index["total_failures"] = index.get("total_failures", 0) + 1

    proj = record.get("project", "unknown")
    if proj not in index["by_project"]:
        index["by_project"][proj] = {"successes": 0, "failures": 0}
    index["by_project"][proj]["successes" if t == "success" else "failures"] += 1

    ftype = record.get("feature_type", "unknown")
    if ftype not in index["by_type"]:
        index["by_type"][ftype] = {"successes": 0, "failures": 0}
    index["by_type"][ftype]["successes" if t == "success" else "failures"] += 1

    index["recent"] = ([{
        "type": t,
        "project": proj,
        "feature_id": record.get("feature_id", ""),
        "label": record.get("label", ""),
        "qa_score": record.get("qa_score", 0),
        "recorded_at": record.get("recorded_at", ""),
    }] + index.get("recent", []))[:50]

    index["updated_at"] = now_iso()
    _write(INDEX_FILE, index)


def get_index() -> dict:
    return _read(INDEX_FILE) or {}


# ── memory context builder ────────────────────────────────────────────────────

def get_memory_context(project: str, feature_type: str, max_chars: int = 1500) -> str:
    """
    Assemble a concise memory context string to inject into AI generation prompts.
    Includes: recent successes for this project/type, top strategies, failure patterns.
    """
    lines = []

    # Recent successes
    all_succ = _load_all(MEM_SUCCESSES)
    relevant = [
        s for s in all_succ
        if s.get("project") == project and s.get("feature_type") == feature_type
    ][:3]
    if relevant:
        lines.append("MEMORY — SUCCESSFUL PATTERNS:")
        for s in relevant:
            lines.append(
                f"  - {s.get('label')} (QA {s.get('qa_score')}/100): {s.get('target_path')}"
            )

    # Top strategies for this project
    strategies = get_all_strategies(project)
    if strategies:
        lines.append("PROVEN STRATEGIES:")
        for st in strategies[:3]:
            key = st.get("strategy_type", "")
            val = st.get("insight", st.get("value", ""))
            if val:
                lines.append(f"  - [{key}] {str(val)[:120]}")

    # Recent learnings
    learnings = get_recent_learnings(1)
    if learnings:
        recent = learnings[0]
        insight = recent.get("key_insight", recent.get("summary", ""))
        if insight:
            lines.append(f"LATEST LEARNING: {str(insight)[:200]}")

    # Failure patterns to avoid
    all_fail = _load_all(MEM_FAILURES)
    proj_fails = [
        f for f in all_fail
        if f.get("project") == project and f.get("feature_type") == feature_type
    ][:2]
    if proj_fails:
        lines.append("AVOID THESE PATTERNS (caused QA failures):")
        for f in proj_fails:
            issues = f.get("qa_issues", [])[:2]
            for issue in issues:
                lines.append(f"  - {issue}")

    context = "\n".join(lines)
    return context[:max_chars] if context else ""


# ── AI-powered learning synthesis ─────────────────────────────────────────────

def synthesize_learnings() -> dict:
    """Call AI to analyze all memory and extract patterns, then save learnings."""
    successes = _load_all(MEM_SUCCESSES)[:20]
    failures = _load_all(MEM_FAILURES)[:20]
    prompts = get_best_prompts(10)
    strategies = get_all_strategies()[:10]

    sys_prompt = """You are a software intelligence analyst for MIFTEH OS.
Analyze operational memory records and extract actionable learnings.
Return valid JSON only."""

    user_prompt = f"""Analyze MIFTEH OS memory records and identify patterns.

RECENT SUCCESSES ({len(successes)}):
{json.dumps([{k: v for k, v in s.items() if k in ('project','feature_type','label','qa_score','qa_grade','target_path','seo_target')} for s in successes[:10]], indent=1)}

RECENT FAILURES ({len(failures)}):
{json.dumps([{k: v for k, v in f.items() if k in ('project','feature_type','error','stage','qa_score','qa_issues')} for f in failures[:10]], indent=1)}

TOP PROMPT PERFORMANCE:
{json.dumps([{k: v for k, v in p.items() if k in ('prompt_key','avg_qa_score','success_rate','runs')} for p in prompts], indent=1)}

Return JSON:
{{
  "key_insight": "<one sentence: most important pattern observed>",
  "summary": "<2-sentence overall health assessment>",
  "success_patterns": ["<pattern 1>", "<pattern 2>", "<pattern 3>"],
  "failure_patterns": ["<what consistently fails and why>"],
  "prompt_recommendations": ["<how to improve prompts based on scores>"],
  "strategy_updates": [
    {{"project": "<project>", "strategy_type": "<type>", "insight": "<what works>"}}
  ],
  "priority_improvements": ["<top 3 things to change right now>"]
}}"""

    data, tokens, cost, ok = generate_json(sys_prompt, user_prompt, max_tokens=1500)
    if not ok or not data:
        return {"key_insight": "AI analysis unavailable", "generated_at": now_iso()}

    # Apply strategy updates
    for su in data.get("strategy_updates", []):
        if su.get("project") and su.get("strategy_type"):
            update_strategy(su["project"], su["strategy_type"], {"insight": su.get("insight", "")})

    result = {**data, "generated_at": now_iso(), "tokens_used": tokens, "cost_usd": cost}
    save_learnings(result)
    print(f"[memory] Learnings synthesized: {data.get('key_insight', '')[:80]}")
    return result


# ── summary for dashboard ─────────────────────────────────────────────────────

def build_memory_summary() -> dict:
    index = get_index()
    successes = _load_all(MEM_SUCCESSES)
    failures = _load_all(MEM_FAILURES)
    prompts = _load_all(MEM_PROMPTS)
    strategies = _load_all(MEM_STRATEGIES)
    learnings = get_recent_learnings(3)

    total = index.get("total_successes", 0) + index.get("total_failures", 0)
    sr = round(index.get("total_successes", 0) / max(total, 1) * 100)

    # QA score trend from successes
    scored = [s.get("qa_score", 0) for s in successes if s.get("qa_score", 0) > 0]
    avg_qa = round(sum(scored) / len(scored)) if scored else 0

    return {
        "generated_at": now_iso(),
        "total_memories": total,
        "total_successes": index.get("total_successes", 0),
        "total_failures": index.get("total_failures", 0),
        "success_rate_pct": sr,
        "avg_qa_score": avg_qa,
        "prompt_count": len(prompts),
        "strategy_count": len(strategies),
        "learning_count": len(learnings),
        "by_project": index.get("by_project", {}),
        "by_type": index.get("by_type", {}),
        "recent": index.get("recent", [])[:20],
        "top_prompts": [
            {k: v for k, v in p.items() if k in ("prompt_key", "avg_qa_score", "success_rate", "runs")}
            for p in get_best_prompts(5)
        ],
        "latest_learning": learnings[0].get("key_insight", "") if learnings else "",
        "success_patterns": learnings[0].get("success_patterns", [])[:3] if learnings else [],
        "priority_improvements": learnings[0].get("priority_improvements", [])[:3] if learnings else [],
    }


def save_memory_summary():
    summary = build_memory_summary()
    out = MEMORY / "memory_summary.json"
    out.write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"[memory] Summary saved → {out}")
    print(f"[memory] {summary['total_successes']} successes, {summary['total_failures']} failures, "
          f"{summary['success_rate_pct']}% success rate, avg QA {summary['avg_qa_score']}/100")
    return summary


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("[memory] Running memory sync...")
    synthesize = os.environ.get("SYNTHESIZE_LEARNINGS", "").lower() in ("1", "true", "yes")
    if synthesize:
        print("[memory] Synthesizing learnings via AI...")
        synthesize_learnings()
    save_memory_summary()
    print("[memory] Done")


if __name__ == "__main__":
    main()
