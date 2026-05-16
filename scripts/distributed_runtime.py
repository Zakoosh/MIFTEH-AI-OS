"""
MIFTEH OS — Distributed Runtime
Parallel workflow execution, queue scheduling, execution workers,
workload balancing, retry orchestration, and execution priorities.
Models GitHub Actions as the distributed execution layer.
"""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")

# Worker pool — each worker maps to a GitHub Actions runner
WORKER_POOL = {
    "worker_seo_1":     {"type": "seo",       "capacity": 3, "project": "all"},
    "worker_seo_2":     {"type": "seo",       "capacity": 3, "project": "all"},
    "worker_exec_1":    {"type": "execution", "capacity": 2, "project": "yallaplays"},
    "worker_exec_2":    {"type": "execution", "capacity": 2, "project": "fionera"},
    "worker_exec_3":    {"type": "execution", "capacity": 2, "project": "mifteh"},
    "worker_intel_1":   {"type": "intel",     "capacity": 5, "project": "all"},
    "worker_qa_1":      {"type": "qa",        "capacity": 4, "project": "all"},
    "worker_economy_1": {"type": "economy",   "capacity": 6, "project": "all"},
}

# Task type → worker type affinity
TASK_AFFINITY = {
    "seo_page":     "seo",
    "seo_hub":      "seo",
    "content":      "seo",
    "execution":    "execution",
    "campaign":     "execution",
    "qa_review":    "qa",
    "intel":        "intel",
    "economy":      "economy",
    "emergency_response": "execution",
}

RETRY_POLICY = {
    "max_attempts": 3,
    "backoff_seconds": [30, 120, 300],
    "retryable_errors": ["timeout", "rate_limit", "network_error"],
    "non_retryable": ["hard_block", "budget_exhausted", "permission_denied"],
}


def load_runtime_state() -> dict:
    f = MEMORY_DIR / "runtime_state.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {
        "created_at": now_iso(),
        "workers": {wid: {**wdata, "active_tasks": [], "completed": 0, "failed": 0,
                          "status": "idle"} for wid, wdata in WORKER_POOL.items()},
        "execution_queue": [],
        "completed_executions": [],
        "failed_executions": [],
        "retry_queue": [],
        "cycle_count": 0,
        "stats": {
            "total_dispatched": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_retried": 0,
        },
    }


def load_task_queue() -> list:
    # Load from agent bus + analytics intelligence
    tasks = []
    bus_f = MEMORY_DIR / "agent_bus.json"
    if bus_f.exists():
        try:
            bus = json.loads(bus_f.read_text())
            tasks.extend([t for t in bus.get("task_queue", []) if t.get("status") == "queued"])
        except Exception:
            pass

    intel_f = MEMORY_DIR / "analytics_intelligence.json"
    if intel_f.exists():
        try:
            intel = json.loads(intel_f.read_text())
            for d in intel.get("autonomous_decisions", [])[:15]:
                tasks.append({
                    "task_id": d.get("decision_id", ""),
                    "type": d.get("type", "seo_page"),
                    "project": d.get("project", ""),
                    "title": d.get("title", ""),
                    "priority": d.get("priority_weight", 5),
                    "source": "analytics_intelligence",
                    "status": "queued",
                })
        except Exception:
            pass

    # Deduplicate by task_id
    seen = set()
    unique = []
    for t in tasks:
        tid = t.get("task_id", "")
        if tid and tid not in seen:
            seen.add(tid)
            unique.append(t)

    return sorted(unique, key=lambda x: x.get("priority", 5), reverse=True)


def find_best_worker(state: dict, task: dict) -> str:
    task_type = task.get("type", "seo_page")
    preferred_type = TASK_AFFINITY.get(task_type, "seo")
    project = task.get("project", "all")

    best_worker = None
    best_score = -1

    for wid, worker in state["workers"].items():
        if len(worker["active_tasks"]) >= worker["capacity"]:
            continue  # at capacity

        affinity_match = 1.0 if worker["type"] == preferred_type else 0.5
        project_match = 1.0 if worker["project"] in (project, "all") else 0.3
        load_factor = 1.0 - (len(worker["active_tasks"]) / max(worker["capacity"], 1))

        score = affinity_match * 0.4 + project_match * 0.3 + load_factor * 0.3
        if score > best_score:
            best_score = score
            best_worker = wid

    return best_worker


def dispatch_task(state: dict, task: dict) -> dict:
    worker_id = find_best_worker(state, task)
    if not worker_id:
        return {"dispatched": False, "reason": "no_worker_available", "task_id": task.get("task_id")}

    worker = state["workers"][worker_id]
    worker["active_tasks"].append(task.get("task_id", ""))
    worker["status"] = "busy" if len(worker["active_tasks"]) >= worker["capacity"] else "active"

    execution = {
        "task_id": task.get("task_id", ""),
        "worker_id": worker_id,
        "task": task,
        "dispatched_at": now_iso(),
        "status": "running",
        "attempts": task.get("attempts", 0) + 1,
    }

    state["execution_queue"].append(execution)
    state["stats"]["total_dispatched"] += 1
    task["status"] = "running"
    task["worker_id"] = worker_id

    return {"dispatched": True, "worker_id": worker_id, "task_id": task.get("task_id")}


def simulate_execution(task: dict) -> dict:
    """
    Simulate task execution result based on task type and project.
    In production this would trigger actual GitHub Actions workflows.
    """
    task_type = task.get("type", "seo_page")
    project = task.get("project", "unknown")

    # Simulate success/failure probabilities by task type
    success_rates = {
        "seo_page": 0.92, "seo_hub": 0.90, "content": 0.95,
        "execution": 0.85, "campaign": 0.88, "qa_review": 0.97,
        "intel": 0.93, "emergency_response": 0.80,
    }
    base_rate = success_rates.get(task_type, 0.85)

    import random
    random.seed(hash(task.get("task_id", "")) % 10000)
    success = random.random() < base_rate

    return {
        "task_id": task.get("task_id"),
        "success": success,
        "simulated": True,
        "execution_ms": int(base_rate * 5000),
        "error": None if success else "simulated_failure",
        "output": {"files_generated": 1, "tokens_used": 1800} if success else {},
    }


def handle_completion(state: dict, execution: dict, result: dict) -> None:
    worker_id = execution.get("worker_id", "")
    task_id = execution.get("task_id", "")

    if worker_id in state["workers"]:
        worker = state["workers"][worker_id]
        if task_id in worker["active_tasks"]:
            worker["active_tasks"].remove(task_id)
        if result["success"]:
            worker["completed"] += 1
        else:
            worker["failed"] += 1
        worker["status"] = "idle" if not worker["active_tasks"] else "active"

    # Move from queue to completed/failed
    state["execution_queue"] = [e for e in state["execution_queue"] if e.get("task_id") != task_id]

    record = {**execution, "result": result, "completed_at": now_iso(),
              "status": "completed" if result["success"] else "failed"}

    if result["success"]:
        state["completed_executions"].append(record)
        state["stats"]["total_completed"] += 1
    else:
        # Check retry eligibility
        attempts = execution.get("attempts", 1)
        error = result.get("error", "")
        if attempts < RETRY_POLICY["max_attempts"] and any(e in str(error) for e in RETRY_POLICY["retryable_errors"]):
            state["retry_queue"].append({**record, "retry_at": now_iso(), "next_attempt": attempts + 1})
            state["stats"]["total_retried"] += 1
        else:
            state["failed_executions"].append(record)
            state["stats"]["total_failed"] += 1

    # Keep history bounded
    if len(state["completed_executions"]) > 100:
        state["completed_executions"] = state["completed_executions"][-100:]
    if len(state["failed_executions"]) > 50:
        state["failed_executions"] = state["failed_executions"][-50:]


def compute_workload_balance(state: dict) -> dict:
    total_capacity = sum(w["capacity"] for w in state["workers"].values())
    total_active = sum(len(w["active_tasks"]) for w in state["workers"].values())
    utilization = round(total_active / max(total_capacity, 1) * 100, 1)

    by_type: dict = {}
    for w in state["workers"].values():
        wt = w["type"]
        if wt not in by_type:
            by_type[wt] = {"capacity": 0, "active": 0}
        by_type[wt]["capacity"] += w["capacity"]
        by_type[wt]["active"] += len(w["active_tasks"])

    bottlenecks = [wt for wt, data in by_type.items()
                   if data["active"] >= data["capacity"]]

    return {
        "total_capacity": total_capacity,
        "total_active": total_active,
        "utilization_pct": utilization,
        "by_type": by_type,
        "bottlenecks": bottlenecks,
        "idle_workers": sum(1 for w in state["workers"].values() if w["status"] == "idle"),
    }


def ai_schedule_optimization(tasks: list, balance: dict) -> dict:
    if not tasks:
        return {"recommendations": [], "priority_adjustments": []}

    system = (
        "You are the MIFTEH OS scheduler AI. Optimize task scheduling "
        "to maximize throughput and minimize resource waste."
    )
    prompt = f"""Pending tasks: {len(tasks)}
Top tasks: {json.dumps(tasks[:5], indent=2)}
Workload balance: {json.dumps(balance, indent=2)}

Optimize scheduling. Respond with JSON:
{{
  "recommendations": [
    {{"action": "description", "expected_impact": "description"}}
  ],
  "priority_adjustments": [
    {{"task_id": "id", "new_priority": 0, "rationale": "why"}}
  ],
  "scheduling_strategy": "description of optimal approach",
  "estimated_throughput_per_hour": 0
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=600)
    if ok and data:
        return data
    return {"recommendations": [], "priority_adjustments": [],
            "scheduling_strategy": "FIFO with priority weighting",
            "estimated_throughput_per_hour": 8}


def main():
    print("[runtime] Starting distributed runtime...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    state = load_runtime_state()
    state["cycle_count"] += 1
    print(f"  [runtime] Cycle #{state['cycle_count']} | {len(WORKER_POOL)} workers available")

    # Load tasks
    tasks = load_task_queue()
    print(f"  [runtime] {len(tasks)} tasks in queue")

    # Dispatch tasks to workers
    dispatched = 0
    results = []
    for task in tasks[:20]:  # Cap per cycle
        dispatch_result = dispatch_task(state, task)
        if dispatch_result["dispatched"]:
            dispatched += 1
            # Simulate execution immediately (in production: triggers workflow)
            exec_record = {
                "task_id": task.get("task_id", ""),
                "worker_id": dispatch_result["worker_id"],
                "task": task,
                "dispatched_at": now_iso(),
                "attempts": 1,
            }
            result = simulate_execution(task)
            handle_completion(state, exec_record, result)
            results.append(result)

    print(f"  [runtime] {dispatched} tasks dispatched")

    # Process retry queue
    retried = 0
    for retry in state["retry_queue"][:5]:
        task = retry.get("task", {})
        task["attempts"] = retry.get("next_attempt", 2)
        dr = dispatch_task(state, task)
        if dr["dispatched"]:
            retried += 1
            exec_record = {**retry, "dispatched_at": now_iso(), "attempts": task["attempts"]}
            result = simulate_execution(task)
            handle_completion(state, exec_record, result)
    state["retry_queue"] = []
    print(f"  [runtime] {retried} retried tasks processed")

    # Compute balance and optimization
    balance = compute_workload_balance(state)
    print(f"  [runtime] Utilization: {balance['utilization_pct']}% | Bottlenecks: {balance['bottlenecks']}")

    schedule_opt = ai_schedule_optimization(tasks[dispatched:dispatched+5], balance)
    throughput = schedule_opt.get("estimated_throughput_per_hour", 0)
    print(f"  [runtime] Est. throughput: {throughput} tasks/hr")

    # Persist state
    state["updated_at"] = now_iso()
    (MEMORY_DIR / "runtime_state.json").write_text(json.dumps(state, indent=2))

    report = {
        "generated_at": now_iso(),
        "cycle": state["cycle_count"],
        "tasks_dispatched": dispatched,
        "tasks_retried": retried,
        "tasks_completed": state["stats"]["total_completed"],
        "tasks_failed": state["stats"]["total_failed"],
        "workload_balance": balance,
        "schedule_optimization": schedule_opt,
        "worker_states": {wid: {"type": w["type"], "status": w["status"],
                                 "active": len(w["active_tasks"]), "capacity": w["capacity"],
                                 "completed": w["completed"]}
                          for wid, w in state["workers"].items()},
        "recent_completions": state["completed_executions"][-10:],
    }

    out = MEMORY_DIR / "runtime_report.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"[runtime] {dispatched} dispatched | {state['stats']['total_completed']} total completed")
    print(f"[runtime] Report → {out}")
    return report


if __name__ == "__main__":
    main()
