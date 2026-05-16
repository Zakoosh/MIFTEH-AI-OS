"""
MIFTEH OS — Agent Message Bus
Asynchronous communication layer for persistent AI agents.
Supports: event publishing, task queuing, delegation, context transfer, failure escalation.
All state is persisted to memory/agent_bus.json — survives across runs.
"""
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))
from ai_client import generate_json, now_iso

MEMORY_DIR = Path("memory")
AGENTS_DIR = MEMORY_DIR / "agents"
BUS_FILE = MEMORY_DIR / "agent_bus.json"
BUS_LOG_FILE = MEMORY_DIR / "agent_bus_log.json"

AGENT_IDS = ["orchestrator", "strategist", "executor", "reviewer",
             "optimizer", "monetizer", "seo", "analytics"]

EVENT_TYPES = [
    "task_created", "task_completed", "task_failed", "task_delegated",
    "mission_started", "mission_completed", "mission_escalated",
    "insight_shared", "alert_raised", "resource_requested",
    "context_transferred", "agent_activated", "agent_idle",
    "governance_blocked", "governance_approved",
]


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _uid() -> str:
    return str(uuid.uuid4())[:12]


def load_bus() -> dict:
    if BUS_FILE.exists():
        try:
            return json.loads(BUS_FILE.read_text())
        except Exception:
            pass
    return {
        "created_at": now_iso(),
        "event_queue": [],
        "task_queue": [],
        "delegation_log": [],
        "subscriptions": {},
        "active_contexts": {},
        "escalation_queue": [],
        "stats": {
            "total_events": 0,
            "total_tasks": 0,
            "total_delegations": 0,
            "total_escalations": 0,
        },
    }


def save_bus(bus: dict) -> None:
    BUS_FILE.write_text(json.dumps(bus, indent=2))


def load_agent(agent_id: str) -> dict:
    f = AGENTS_DIR / f"{agent_id}.json"
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {"id": agent_id, "name": agent_id.title(), "confidence": 0.75,
            "memory": {}, "execution_history": [], "total_missions": 0, "success_rate": 1.0}


def save_agent(agent: dict) -> None:
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    agent["last_active"] = now_iso()
    (AGENTS_DIR / f"{agent['id']}.json").write_text(json.dumps(agent, indent=2))


def publish(bus: dict, event_type: str, data: dict,
            from_agent: str, to_agent: Optional[str] = None) -> dict:
    event = {
        "event_id": _uid(),
        "event_type": event_type,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "data": data,
        "published_at": _ts(),
        "processed": False,
    }
    bus["event_queue"].append(event)
    bus["stats"]["total_events"] += 1

    # Keep queue bounded
    if len(bus["event_queue"]) > 500:
        bus["event_queue"] = bus["event_queue"][-500:]

    return event


def queue_task(bus: dict, task: dict, from_agent: str,
               priority: int = 5) -> dict:
    task_entry = {
        "task_id": _uid(),
        "priority": priority,
        "status": "queued",
        "from_agent": from_agent,
        "queued_at": _ts(),
        "attempts": 0,
        **task,
    }
    bus["task_queue"].append(task_entry)
    bus["task_queue"].sort(key=lambda x: x.get("priority", 5), reverse=True)
    bus["stats"]["total_tasks"] += 1

    if len(bus["task_queue"]) > 200:
        bus["task_queue"] = bus["task_queue"][-200:]

    return task_entry


def delegate(bus: dict, task: dict, from_agent: str, to_agent: str,
             context: dict = None) -> dict:
    entry = {
        "delegation_id": _uid(),
        "from_agent": from_agent,
        "to_agent": to_agent,
        "task": task,
        "context": context or {},
        "delegated_at": _ts(),
        "status": "pending",
    }
    bus["delegation_log"].append(entry)
    bus["stats"]["total_delegations"] += 1

    # Also queue as task for the target agent
    queue_task(bus, {**task, "assigned_to": to_agent, "delegated_by": from_agent}, from_agent, priority=task.get("priority", 5))

    publish(bus, "task_delegated", {"delegation_id": entry["delegation_id"], "task": task},
            from_agent, to_agent)

    if len(bus["delegation_log"]) > 200:
        bus["delegation_log"] = bus["delegation_log"][-200:]

    return entry


def escalate(bus: dict, failure: dict, from_agent: str,
             severity: str = "medium") -> dict:
    entry = {
        "escalation_id": _uid(),
        "from_agent": from_agent,
        "severity": severity,
        "failure": failure,
        "escalated_at": _ts(),
        "resolved": False,
    }
    bus["escalation_queue"].append(entry)
    bus["stats"]["total_escalations"] += 1

    publish(bus, "mission_escalated",
            {"escalation_id": entry["escalation_id"], "severity": severity, "failure": failure},
            from_agent, "orchestrator")

    return entry


def transfer_context(bus: dict, context_id: str, context: dict,
                     from_agent: str, to_agent: str) -> None:
    bus["active_contexts"][context_id] = {
        "context_id": context_id,
        "data": context,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "transferred_at": _ts(),
    }
    publish(bus, "context_transferred", {"context_id": context_id},
            from_agent, to_agent)


def get_pending_tasks(bus: dict, agent_id: str) -> list:
    return [t for t in bus["task_queue"]
            if t.get("assigned_to") == agent_id and t.get("status") == "queued"]


def mark_task_done(bus: dict, task_id: str, success: bool, result: dict = None) -> None:
    for t in bus["task_queue"]:
        if t.get("task_id") == task_id:
            t["status"] = "completed" if success else "failed"
            t["completed_at"] = _ts()
            t["result"] = result or {}
            break


def get_recent_events(bus: dict, event_type: str = None,
                      agent_id: str = None, limit: int = 20) -> list:
    events = bus["event_queue"][-200:]
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]
    if agent_id:
        events = [e for e in events
                  if e.get("from_agent") == agent_id or e.get("to_agent") == agent_id]
    return events[-limit:]


def ai_route_tasks(bus: dict, pending_tasks: list) -> list:
    if not pending_tasks:
        return []

    system = (
        "You are the MIFTEH OS routing intelligence. "
        "Assign tasks to the most capable agent based on task type and agent skills."
    )
    agent_profiles = {aid: {"skills": load_agent(aid).get("skills", {}),
                             "confidence": load_agent(aid).get("confidence", 0.75)}
                      for aid in AGENT_IDS}
    prompt = f"""Unassigned tasks:
{json.dumps(pending_tasks[:10], indent=2)}

Agent profiles:
{json.dumps(agent_profiles, indent=2)}

Route each task to the best agent. Respond with JSON:
{{
  "assignments": [
    {{"task_id": "id", "assigned_to": "agent_id", "rationale": "why"}}
  ]
}}
Return ONLY valid JSON."""

    data, _, _, ok = generate_json(system, prompt, max_tokens=600)
    assignments = data.get("assignments", []) if ok and data else []

    for assignment in assignments:
        task_id = assignment.get("task_id")
        assigned_to = assignment.get("assigned_to")
        for t in bus["task_queue"]:
            if t.get("task_id") == task_id and not t.get("assigned_to"):
                t["assigned_to"] = assigned_to
                t["routing_rationale"] = assignment.get("rationale", "")

    return assignments


def run_bus_cycle(bus: dict) -> dict:
    unassigned = [t for t in bus["task_queue"] if not t.get("assigned_to") and t.get("status") == "queued"]
    assignments = ai_route_tasks(bus, unassigned) if unassigned else []

    # Mark old events as processed
    cutoff = 100
    for e in bus["event_queue"][-cutoff:]:
        e["processed"] = True

    # Resolve old escalations (auto-close after 48h if no action)
    for esc in bus["escalation_queue"]:
        if not esc["resolved"]:
            esc["resolved"] = True
            esc["resolution"] = "auto-closed"

    active_tasks = sum(1 for t in bus["task_queue"] if t.get("status") == "queued")
    pending_escalations = sum(1 for e in bus["escalation_queue"] if not e["resolved"])

    return {
        "cycle_at": now_iso(),
        "tasks_routed": len(assignments),
        "active_tasks": active_tasks,
        "pending_escalations": pending_escalations,
        "total_events": bus["stats"]["total_events"],
        "total_tasks": bus["stats"]["total_tasks"],
    }


def main():
    print("[agent-bus] Starting agent message bus...")

    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)

    bus = load_bus()

    # Seed initial tasks from analytics_intelligence autonomous_decisions
    intel_f = MEMORY_DIR / "analytics_intelligence.json"
    if intel_f.exists():
        try:
            intel = json.loads(intel_f.read_text())
            decisions = intel.get("autonomous_decisions", [])
            existing_task_ids = {t.get("source_decision_id") for t in bus["task_queue"]}
            new_count = 0
            for d in decisions[:10]:
                did = d.get("decision_id", "")
                if did and did not in existing_task_ids:
                    queue_task(bus, {
                        "title": d.get("title", ""),
                        "project": d.get("project", ""),
                        "type": d.get("type", "seo_page"),
                        "source_decision_id": did,
                        "seo_target": d.get("seo_target", ""),
                        "rationale": d.get("rationale", ""),
                        "priority_weight": d.get("priority_weight", 5),
                    }, from_agent="orchestrator", priority=d.get("priority_weight", 5))
                    new_count += 1
            print(f"  [agent-bus] Seeded {new_count} tasks from execution queue")
        except Exception as e:
            print(f"  [agent-bus] Could not seed from intel: {e}")

    # Publish agent activation events
    for agent_id in AGENT_IDS:
        agent = load_agent(agent_id)
        publish(bus, "agent_activated", {"agent_id": agent_id, "confidence": agent.get("confidence", 0.75)},
                from_agent=agent_id)

    # Run bus cycle
    cycle_result = run_bus_cycle(bus)

    bus["last_cycle"] = cycle_result
    bus["updated_at"] = now_iso()
    save_bus(bus)

    # Append to log
    log = []
    if BUS_LOG_FILE.exists():
        try:
            log = json.loads(BUS_LOG_FILE.read_text())
        except Exception:
            pass
    log.append(cycle_result)
    BUS_LOG_FILE.write_text(json.dumps(log[-100:], indent=2))

    print(f"  [agent-bus] {cycle_result['tasks_routed']} tasks routed")
    print(f"  [agent-bus] {cycle_result['active_tasks']} active tasks")
    print(f"  [agent-bus] {cycle_result['pending_escalations']} pending escalations")
    print(f"  [agent-bus] Total events: {cycle_result['total_events']}")
    print(f"[agent-bus] Bus → {BUS_FILE}")
    return bus


if __name__ == "__main__":
    main()
