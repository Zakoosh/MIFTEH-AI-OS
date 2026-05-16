"""
MIFTEH OS — Production Observability
Deployment latency, AI call latency, workflow bottlenecks,
memory retrieval performance, tool execution metrics,
agent activity heatmaps, error propagation tracking.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

TRACKED_WORKFLOWS = [
    "ai-seo-optimizer", "ai-product-executor", "ai-growth-engine",
    "ai-monetization-runtime", "ai-conversion-engine", "ai-acquisition-engine",
    "ai-scaling-engine", "ai-agent-bus", "ai-cognition-engine",
    "ai-governance-engine", "ai-distributed-runtime", "ai-task-economy",
    "ai-agent-evolution", "ai-operations-kernel", "ai-civilization",
    "ai-deployment-pipeline", "ai-vector-memory", "ai-retrieval-engine",
    "ai-tool-runtime", "ai-research-engine", "ai-sandbox-engine",
    "ai-observability-engine",
]

SCRIPT_REPORT_MAP = {
    "ai-growth-engine":        "growth_report.json",
    "ai-monetization-runtime": "monetization_runtime_report.json",
    "ai-conversion-engine":    "conversion_report.json",
    "ai-acquisition-engine":   "acquisition_report.json",
    "ai-scaling-engine":       "scaling_report.json",
    "ai-cognition-engine":     "cognition_report.json",
    "ai-governance-engine":    "governance_report.json",
    "ai-distributed-runtime":  "runtime_report.json",
    "ai-task-economy":         "task_economy_report.json",
    "ai-operations-kernel":    "kernel_report.json",
    "ai-agent-evolution":      "agent_evolution_report.json",
    "ai-deployment-pipeline":  "deployment_pipeline_report.json",
    "ai-vector-memory":        "vector_stats.json",
    "ai-retrieval-engine":     "retrieval_results.json",
    "ai-tool-runtime":         "tool_runtime_report.json",
    "ai-research-engine":      "research_report.json",
    "ai-sandbox-engine":       "sandbox_report.json",
}

SLA_THRESHOLDS = {
    "workflow_latency_warn_min": 5,
    "workflow_latency_crit_min": 15,
    "ai_cost_warn_usd": 0.50,
    "ai_cost_crit_usd": 2.00,
    "memory_size_warn_mb": 30,
    "memory_size_crit_mb": 100,
    "tool_success_rate_warn_pct": 80,
}


def _rj(path, default=None):
    f = MEMORY_DIR / path
    try:
        return json.loads(f.read_text()) if f.exists() else (default or {})
    except Exception:
        return default or {}


def measure_workflow_recency():
    """Measure how recently each workflow ran by checking report file timestamps."""
    now = datetime.now(timezone.utc)
    metrics = []

    for workflow, report_file in SCRIPT_REPORT_MAP.items():
        f = MEMORY_DIR / report_file
        if f.exists():
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
                age_hours = (now - mtime).total_seconds() / 3600
                data = json.loads(f.read_text())
                generated_at = data.get("generated_at", "")

                metrics.append({
                    "workflow": workflow,
                    "report_file": report_file,
                    "last_run_at": generated_at or mtime.isoformat(),
                    "age_hours": round(age_hours, 1),
                    "status": "fresh" if age_hours < 25 else ("stale" if age_hours < 72 else "missing"),
                    "tokens_used": data.get("tokens_used", 0),
                    "cost_usd": data.get("cost_usd", 0.0),
                    "ai_generated": data.get("ai_generated", False),
                })
            except Exception:
                pass
        else:
            metrics.append({
                "workflow": workflow,
                "report_file": report_file,
                "last_run_at": None,
                "age_hours": None,
                "status": "never_run",
                "tokens_used": 0,
                "cost_usd": 0.0,
            })

    return metrics


def compute_ai_latency_estimates():
    """Estimate AI call latency from cost/token data across all reports."""
    estimates = []
    for workflow, report_file in SCRIPT_REPORT_MAP.items():
        data = _rj(report_file)
        tokens = data.get("tokens_used", 0)
        cost = data.get("cost_usd", 0.0)
        if tokens > 0:
            # Estimate: ~1000 tokens/sec for gpt-4o-mini equivalent
            est_latency_sec = round(tokens / 1000, 1)
            estimates.append({
                "workflow": workflow,
                "tokens": tokens,
                "cost_usd": cost,
                "estimated_latency_sec": est_latency_sec,
            })

    return sorted(estimates, key=lambda x: x["estimated_latency_sec"], reverse=True)


def detect_workflow_bottlenecks(workflow_metrics, ai_latency):
    """Find bottlenecks: stale workflows, expensive scripts, failures."""
    bottlenecks = []

    stale = [m for m in workflow_metrics if m["status"] in ("stale", "never_run")]
    if stale:
        bottlenecks.append({
            "type": "stale_workflow",
            "severity": "warning",
            "details": f"{len(stale)} workflows haven't run recently",
            "affected": [m["workflow"] for m in stale[:3]],
        })

    expensive = [l for l in ai_latency if l["cost_usd"] > SLA_THRESHOLDS["ai_cost_warn_usd"]]
    if expensive:
        bottlenecks.append({
            "type": "high_cost_script",
            "severity": "warning",
            "details": f"{len(expensive)} scripts exceed cost threshold ${SLA_THRESHOLDS['ai_cost_warn_usd']}",
            "affected": [l["workflow"] for l in expensive[:3]],
        })

    # Check memory size
    mem_size = sum(f.stat().st_size for f in MEMORY_DIR.rglob("*.json") if f.is_file()) / (1024 * 1024)
    if mem_size > SLA_THRESHOLDS["memory_size_warn_mb"]:
        bottlenecks.append({
            "type": "memory_growth",
            "severity": "warning" if mem_size < SLA_THRESHOLDS["memory_size_crit_mb"] else "critical",
            "details": f"Memory directory is {mem_size:.1f}MB",
            "affected": ["memory/"],
        })

    return bottlenecks


def build_agent_activity_heatmap():
    """Build an activity heatmap per agent from agent bus and kernel data."""
    bus = _rj("agent_bus.json")
    kernel = _rj("kernel_report.json")

    agent_states = kernel.get("agent_states", {})
    events = bus.get("event_queue", [])

    heatmap = {}
    for agent_id in ["orchestrator", "strategist", "executor", "reviewer", "optimizer", "monetizer", "seo", "analytics"]:
        state = agent_states.get(agent_id, {})
        agent_events = [e for e in events if e.get("from_agent") == agent_id or e.get("to_agent") == agent_id]
        heatmap[agent_id] = {
            "status": state.get("status", "unknown"),
            "total_missions": state.get("total_missions", 0),
            "success_rate": state.get("success_rate", 1.0),
            "confidence": state.get("confidence", 0),
            "activity_level": "high" if len(agent_events) > 5 else ("medium" if len(agent_events) > 1 else "low"),
            "event_count": len(agent_events),
        }
    return heatmap


def track_error_propagation():
    """Detect error patterns from various report files."""
    errors = []

    # Deployment rollback triggers
    deploy = _rj("deployment_pipeline_report.json")
    for pid, pdata in deploy.get("projects", {}).items():
        triggers = pdata.get("rollback_triggers", [])
        for t in triggers:
            errors.append({"source": "deployment", "project": pid, "error": t, "severity": "high"})

    # Trust score failures
    trust = _rj("trust_scores.json")
    for repo, rdata in trust.get("repos", {}).items():
        if rdata.get("rollback_count", 0) > 0:
            errors.append({
                "source": "trust_system",
                "project": repo,
                "error": f"{rdata['rollback_count']} rollbacks recorded",
                "severity": "medium",
            })

    # Governance blocks
    gov = _rj("governance_report.json")
    blocked = gov.get("blocked_actions", 0)
    if blocked > 0:
        errors.append({"source": "governance", "project": "system", "error": f"{blocked} actions blocked", "severity": "low"})

    return errors[:20]


def compute_memory_retrieval_performance():
    """Measure retrieval engine performance from its results."""
    retrieval = _rj("retrieval_results.json")
    if not retrieval:
        return {"status": "not_run", "avg_hits_per_query": 0}

    results = retrieval.get("results", {})
    if not results:
        return {"status": "empty", "avg_hits_per_query": 0}

    total_hits = sum(r.get("memory_count", 0) for r in results.values())
    avg_hits = round(total_hits / max(len(results), 1), 1)

    methods_used = {}
    for qres in results.values():
        for mem in qres.get("memories", []):
            method = mem.get("retrieval_method", "keyword")
            methods_used[method] = methods_used.get(method, 0) + 1

    return {
        "status": "operational",
        "queries_run": len(results),
        "total_hits": total_hits,
        "avg_hits_per_query": avg_hits,
        "index_size": retrieval.get("index_size", 0),
        "embedded_memories": retrieval.get("embedded_memories", 0),
        "retrieval_methods": methods_used,
    }


def ai_observability_analysis(bottlenecks, workflow_metrics, ai_latency, errors):
    """AI synthesizes observability data into actionable insights."""
    system = (
        "You are an SRE analyzing production AI system observability data. "
        "Return valid JSON only."
    )
    fresh = sum(1 for m in workflow_metrics if m["status"] == "fresh")
    total_cost = sum(l["cost_usd"] for l in ai_latency)
    prompt = f"""System observability snapshot:
Workflows monitored: {len(workflow_metrics)} ({fresh} fresh, {len(workflow_metrics)-fresh} stale/missing)
Total AI cost tracked: ${total_cost:.4f}
Bottlenecks detected: {len(bottlenecks)}
Error propagation events: {len(errors)}
Retrieval queries running: {len(ai_latency)}

Return observability analysis:
{{
  "system_observability_score": 0-100,
  "operational_status": "green|yellow|red",
  "executive_summary": "2-sentence system observability overview",
  "critical_alerts": ["alert1"],
  "top_bottleneck": "most impactful bottleneck",
  "optimization_opportunities": ["opp1", "opp2"],
  "sla_status": {{
    "workflow_freshness": "pass|warn|fail",
    "cost_efficiency": "pass|warn|fail",
    "error_rate": "pass|warn|fail"
  }},
  "next_actions": ["action1", "action2"]
}}"""

    data, tokens, cost, ok = generate_json(system, prompt, 400)
    if not ok:
        score = max(0, 100 - len(bottlenecks) * 10 - len(errors) * 5)
        data = {
            "system_observability_score": score,
            "operational_status": "green" if score >= 70 else ("yellow" if score >= 40 else "red"),
            "executive_summary": f"{fresh}/{len(workflow_metrics)} workflows fresh. {len(bottlenecks)} bottlenecks, {len(errors)} errors.",
            "critical_alerts": [b["details"] for b in bottlenecks if b["severity"] == "critical"],
            "top_bottleneck": bottlenecks[0]["details"] if bottlenecks else "None",
            "optimization_opportunities": ["Reduce stale workflow count", "Optimize high-cost scripts"],
            "sla_status": {"workflow_freshness": "pass" if fresh > len(workflow_metrics) * 0.7 else "warn", "cost_efficiency": "pass", "error_rate": "pass" if len(errors) < 5 else "warn"},
            "next_actions": ["Review stale workflows", "Run scaling_engine for token optimization"],
        }
    return data, tokens, cost


def main():
    print("[observability_engine] Starting observability sweep...")

    workflow_metrics = measure_workflow_recency()
    ai_latency = compute_ai_latency_estimates()
    bottlenecks = detect_workflow_bottlenecks(workflow_metrics, ai_latency)
    agent_heatmap = build_agent_activity_heatmap()
    error_propagation = track_error_propagation()
    retrieval_perf = compute_memory_retrieval_performance()

    analysis, tokens, cost = ai_observability_analysis(bottlenecks, workflow_metrics, ai_latency, error_propagation)

    fresh_count = sum(1 for m in workflow_metrics if m["status"] == "fresh")
    total_ai_cost = sum(l["cost_usd"] for l in ai_latency)

    report = {
        "generated_at": now_iso(),
        "observability_score": analysis.get("system_observability_score", 0),
        "operational_status": analysis.get("operational_status", "unknown"),
        "workflow_metrics": workflow_metrics,
        "fresh_workflow_count": fresh_count,
        "stale_workflow_count": len(workflow_metrics) - fresh_count,
        "ai_latency_estimates": ai_latency[:10],
        "total_tracked_ai_cost_usd": round(total_ai_cost, 6),
        "bottlenecks": bottlenecks,
        "agent_heatmap": agent_heatmap,
        "error_propagation": error_propagation,
        "memory_retrieval_performance": retrieval_perf,
        "ai_analysis": analysis,
        "tokens_used": tokens,
        "cost_usd": round(cost, 6),
        "ai_generated": True,
    }

    (MEMORY_DIR / "observability_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    score = analysis.get("system_observability_score", 0)
    status = analysis.get("operational_status", "?")
    print(f"[observability_engine] Done — score {score}/100 [{status}], {fresh_count} fresh workflows, ${cost:.4f}")


if __name__ == "__main__":
    main()
