"""
MIFTEH OS — Execution Sandbox
Isolated execution environments, experimental branches,
temporary memory snapshots, safe testing, rollback checkpoints.
Provides safe experimentation before production execution.
"""
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
SANDBOXES_DIR = MEMORY_DIR / "sandboxes"
CHECKPOINTS_DIR = MEMORY_DIR / "checkpoints"
SANDBOX_REPORT_FILE = MEMORY_DIR / "sandbox_report.json"

MAX_SANDBOXES = 5
MAX_CHECKPOINTS_PER_TYPE = 3

SANDBOX_TYPES = {
    "strategy_test": {
        "description": "Test a new SEO or growth strategy before committing",
        "files_to_snapshot": ["growth_report.json", "seo_opportunities.json"],
        "risk_level": "low",
        "auto_expire_hours": 24,
    },
    "monetization_test": {
        "description": "Experiment with pricing or conversion changes",
        "files_to_snapshot": ["monetization_runtime_report.json", "conversion_report.json"],
        "risk_level": "medium",
        "auto_expire_hours": 48,
    },
    "agent_experiment": {
        "description": "Test agent behavior changes in isolation",
        "files_to_snapshot": ["agent_bus.json", "cognition_state.json"],
        "risk_level": "medium",
        "auto_expire_hours": 12,
    },
    "deployment_preview": {
        "description": "Preview deployment before production push",
        "files_to_snapshot": ["deployment_pipeline_report.json"],
        "risk_level": "low",
        "auto_expire_hours": 6,
    },
}

EXPERIMENT_TEMPLATES = [
    {
        "id": "seo_cluster_test",
        "type": "strategy_test",
        "hypothesis": "Adding 5 FAQ pages to top cluster will increase indexed pages by 20%",
        "metrics": ["indexed_pages", "organic_traffic", "topical_authority_score"],
        "success_criteria": "Traffic increase >15% within 30 days",
        "rollback_condition": "Traffic decrease >10% within 14 days",
    },
    {
        "id": "cta_text_test",
        "type": "monetization_test",
        "hypothesis": "Changing primary CTA from generic to benefit-focused increases CTR by 25%",
        "metrics": ["ctr", "conversion_rate", "revenue_per_visit"],
        "success_criteria": "CTR increase >20% within 14 days",
        "rollback_condition": "Conversion rate decrease >15% within 7 days",
    },
    {
        "id": "agent_confidence_boost",
        "type": "agent_experiment",
        "hypothesis": "Increasing orchestrator confidence threshold improves decision quality",
        "metrics": ["decisions_quality_score", "escalation_rate", "task_success_rate"],
        "success_criteria": "Quality score +10 within 2 cycles",
        "rollback_condition": "Escalation rate >30% within 1 cycle",
    },
]


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def load_sandbox_registry():
    f = SANDBOXES_DIR / "registry.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {"sandboxes": {}, "created_count": 0}


def save_sandbox_registry(registry):
    SANDBOXES_DIR.mkdir(exist_ok=True)
    (SANDBOXES_DIR / "registry.json").write_text(json.dumps(registry, indent=2))


def create_checkpoint(checkpoint_name, files_to_snapshot):
    """Create a memory checkpoint (snapshot of specific files)."""
    CHECKPOINTS_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    checkpoint_dir = CHECKPOINTS_DIR / f"{checkpoint_name}_{ts}"
    checkpoint_dir.mkdir(exist_ok=True)

    snapshot_files = []
    for fname in files_to_snapshot:
        src = MEMORY_DIR / fname
        if src.exists():
            dst = checkpoint_dir / fname
            shutil.copy2(src, dst)
            snapshot_files.append(fname)

    meta = {
        "name": checkpoint_name,
        "created_at": now_iso(),
        "files": snapshot_files,
        "path": str(checkpoint_dir.relative_to(MEMORY_DIR)),
    }
    (checkpoint_dir / "_meta.json").write_text(json.dumps(meta, indent=2))
    return meta


def create_sandbox(sandbox_type, experiment_id=None):
    """Create an isolated sandbox environment."""
    config = SANDBOX_TYPES.get(sandbox_type, SANDBOX_TYPES["strategy_test"])
    SANDBOXES_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    sandbox_id = f"{sandbox_type}_{ts}"
    sandbox_dir = SANDBOXES_DIR / sandbox_id
    sandbox_dir.mkdir(exist_ok=True)

    # Copy files into sandbox
    snapshot_files = []
    for fname in config["files_to_snapshot"]:
        src = MEMORY_DIR / fname
        if src.exists():
            shutil.copy2(src, sandbox_dir / fname)
            snapshot_files.append(fname)

    sandbox_meta = {
        "id": sandbox_id,
        "type": sandbox_type,
        "experiment_id": experiment_id,
        "created_at": now_iso(),
        "risk_level": config["risk_level"],
        "status": "active",
        "snapshotted_files": snapshot_files,
        "path": str(sandbox_dir.relative_to(MEMORY_DIR)),
        "auto_expire_hours": config["auto_expire_hours"],
    }
    (sandbox_dir / "_sandbox_meta.json").write_text(json.dumps(sandbox_meta, indent=2))
    return sandbox_meta


def restore_from_checkpoint(checkpoint_path):
    """Restore memory files from a checkpoint (rollback)."""
    cp_dir = MEMORY_DIR / checkpoint_path
    if not cp_dir.exists():
        return {"success": False, "error": f"Checkpoint not found: {checkpoint_path}"}

    restored = []
    for f in cp_dir.iterdir():
        if f.name == "_meta.json" or not f.name.endswith(".json"):
            continue
        dst = MEMORY_DIR / f.name
        shutil.copy2(f, dst)
        restored.append(f.name)

    return {"success": True, "restored_files": restored, "checkpoint": checkpoint_path}


def expire_old_sandboxes(registry):
    """Mark and clean up expired sandboxes."""
    now = datetime.now(timezone.utc)
    expired = []
    for sid, meta in list(registry.get("sandboxes", {}).items()):
        if meta.get("status") == "expired":
            continue
        created = datetime.fromisoformat(meta["created_at"].replace("Z", "+00:00"))
        age_hours = (now - created).total_seconds() / 3600
        if age_hours > meta.get("auto_expire_hours", 24):
            registry["sandboxes"][sid]["status"] = "expired"
            expired.append(sid)
    return expired


def score_experiment(experiment):
    """Score an experiment design for completeness and risk."""
    score = 0
    if experiment.get("hypothesis"):
        score += 25
    if experiment.get("metrics"):
        score += 25
    if experiment.get("success_criteria"):
        score += 25
    if experiment.get("rollback_condition"):
        score += 25
    return score


def ai_sandbox_recommendations(experiments, sandbox_registry):
    """AI recommends which experiments to run next."""
    system = "You are a product experimentation expert. Recommend experiment prioritization. Return valid JSON only."
    scored = [{"id": e["id"], "type": e["type"], "score": score_experiment(e)} for e in experiments]
    prompt = f"""Experiment templates: {json.dumps(scored)}
Active sandboxes: {len([s for s in sandbox_registry.get('sandboxes', {}).values() if s.get('status') == 'active'])}
Max sandboxes: {MAX_SANDBOXES}

Return experiment recommendations:
{{
  "recommended_next_experiment": "experiment_id",
  "reasoning": "why this experiment first",
  "risk_assessment": "low|medium|high",
  "expected_learnings": ["learning1", "learning2"],
  "concurrent_safe": ["experiment_id1"],
  "experiment_velocity": "recommended experiments per week"
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 300)
    if not ok:
        data = {
            "recommended_next_experiment": experiments[0]["id"] if experiments else "none",
            "reasoning": "Highest ROI experiment with lowest risk should run first",
            "risk_assessment": "low",
            "expected_learnings": ["CTA impact on conversion", "SEO cluster velocity"],
            "concurrent_safe": [experiments[1]["id"]] if len(experiments) > 1 else [],
            "experiment_velocity": "2 experiments/week",
        }
    return data, tokens, cost


def main():
    print("[sandbox_engine] Starting sandbox cycle...")
    SANDBOXES_DIR.mkdir(exist_ok=True)
    CHECKPOINTS_DIR.mkdir(exist_ok=True)

    registry = load_sandbox_registry()

    # Expire old sandboxes
    expired = expire_old_sandboxes(registry)
    if expired:
        print(f"[sandbox_engine] Expired {len(expired)} sandboxes")

    # Create fresh checkpoints for critical memory files
    checkpoints_created = []
    checkpoint_groups = {
        "seo_snapshot": ["seo_opportunities.json", "growth_report.json"],
        "monetization_snapshot": ["monetization_runtime_report.json", "conversion_report.json"],
        "agent_snapshot": ["agent_bus.json"],
    }
    for name, files in checkpoint_groups.items():
        cp = create_checkpoint(name, files)
        checkpoints_created.append(cp)

    # Create one new sandbox for the highest-priority experiment
    new_sandbox = None
    if len([s for s in registry.get("sandboxes", {}).values() if s.get("status") == "active"]) < MAX_SANDBOXES:
        new_sandbox = create_sandbox("strategy_test", experiment_id="seo_cluster_test")
        registry.setdefault("sandboxes", {})[new_sandbox["id"]] = new_sandbox
        registry["created_count"] = registry.get("created_count", 0) + 1
        print(f"[sandbox_engine] Created sandbox: {new_sandbox['id']}")

    # Score all experiment templates
    scored_experiments = [
        {**exp, "design_score": score_experiment(exp)}
        for exp in EXPERIMENT_TEMPLATES
    ]

    ai_recs, tokens, cost = ai_sandbox_recommendations(EXPERIMENT_TEMPLATES, registry)

    save_sandbox_registry(registry)

    active_sandboxes = [s for s in registry.get("sandboxes", {}).values() if s.get("status") == "active"]
    report = {
        "generated_at": now_iso(),
        "active_sandboxes": len(active_sandboxes),
        "expired_this_cycle": len(expired),
        "checkpoints_created": len(checkpoints_created),
        "total_checkpoints": len(checkpoints_created),
        "experiment_templates": scored_experiments,
        "active_sandbox_list": active_sandboxes[:5],
        "new_sandbox": new_sandbox,
        "ai_recommendations": ai_recs,
        "tokens_used": tokens,
        "cost_usd": round(cost, 6),
        "ai_generated": True,
    }

    SANDBOX_REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"[sandbox_engine] Done — {len(active_sandboxes)} active sandboxes, {len(checkpoints_created)} checkpoints, ${cost:.4f}")


if __name__ == "__main__":
    main()
