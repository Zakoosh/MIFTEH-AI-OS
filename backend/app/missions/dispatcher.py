from datetime import datetime

from app.agents.models import AgentMetadata
from app.agents.agency_bridge import read_agent_file
from app.missions.models import AgentResult, AgentFinding


def _build_mission_prompt(
    agent_content: str,
    mission_title: str,
    mission_id: str,
    project_name: str,
    goal: str,
    expected_output: list[str],
) -> str:
    output_lines = "\n".join(f"- {item}" for item in expected_output)

    return f"""You are running inside MIFTEH AI OS.

=== ORIGINAL AGENCY AGENT ===
{agent_content}

=== PROJECT ===
Project: {project_name}
Goal: {goal}

=== MISSION ===
Mission ID: {mission_id}
Mission Title: {mission_title}

Expected Output:
{output_lines}

=== INSTRUCTIONS ===
Produce a structured report with the following sections:

1. **Summary**: Brief overview of your analysis
2. **Findings**: Key observations about the project
3. **Risks**: Potential issues or concerns
4. **Suggested Actions**: Specific actionable improvements
5. **Priority Level**: critical / high / medium / low

Be direct, practical, and specific. Think like an autonomous project improvement agent.
"""


def _parse_finding(content: str) -> AgentFinding:
    finding = AgentFinding()
    current_section = ""

    for line in content.split("\n"):
        stripped = line.strip().lower()

        if "summary" in stripped and ("**" in line or "#" in line):
            current_section = "summary"
            continue
        elif "finding" in stripped and ("**" in line or "#" in line):
            current_section = "findings"
            continue
        elif "risk" in stripped and ("**" in line or "#" in line):
            current_section = "risks"
            continue
        elif ("action" in stripped or "suggest" in stripped) and ("**" in line or "#" in line):
            current_section = "actions"
            continue
        elif "priority" in stripped and ("**" in line or "#" in line):
            current_section = "priority"
            continue

        clean = line.strip().lstrip("-*• ").strip()
        if not clean:
            continue

        if current_section == "summary":
            finding.summary += clean + " "
        elif current_section == "findings":
            finding.findings.append(clean)
        elif current_section == "risks":
            finding.risks.append(clean)
        elif current_section == "actions":
            finding.actions.append(clean)
        elif current_section == "priority":
            for level in ("critical", "high", "medium", "low"):
                if level in clean.lower():
                    finding.priority = level
                    break

    finding.summary = finding.summary.strip()

    if not finding.summary and content:
        finding.summary = content[:200].strip()

    return finding


def _run_offline_mock(agent_name: str, mission_title: str) -> dict:
    return {
        "mode": "offline_mock",
        "success": False,
        "content": (
            f"OFFLINE MOCK REPORT for {agent_name}\n\n"
            f"Mission: {mission_title}\n\n"
            "The execution pipeline is structurally working.\n"
            "OpenAI API is currently unavailable.\n\n"
            "**Summary**\nOffline mock — no real analysis performed.\n\n"
            "**Findings**\n- Pipeline reached the AI execution layer\n"
            "- Agent was loaded successfully\n\n"
            "**Risks**\n- No real analysis available in offline mode\n\n"
            "**Suggested Actions**\n- Re-run when OpenAI API is available\n\n"
            "**Priority Level**\n- low\n"
        ),
    }


def dispatch_agent(
    agent: AgentMetadata,
    mission_title: str,
    mission_id: str,
    project_name: str,
    goal: str,
    expected_output: list[str],
) -> AgentResult:
    started_at = datetime.now().isoformat()

    agent_content = read_agent_file(agent.source_path)

    if agent_content is None:
        return AgentResult(
            agent_name=agent.name,
            division=agent.division,
            source_path=agent.source_path,
            status="failed",
            mode="error",
            success=False,
            error=f"Could not read agent file: {agent.source_path}",
            started_at=started_at,
            completed_at=datetime.now().isoformat(),
        )

    prompt = _build_mission_prompt(
        agent_content=agent_content,
        mission_title=mission_title,
        mission_id=mission_id,
        project_name=project_name,
        goal=goal,
        expected_output=expected_output,
    )

    try:
        from app.engine.agent_runner import run_agent
        result = run_agent(prompt)
    except Exception as exc:
        result = _run_offline_mock(agent.name, mission_title)
        result["error"] = str(exc)

    if not result.get("success", False):
        mock = _run_offline_mock(agent.name, mission_title)
        if not result.get("content"):
            result["content"] = mock["content"]

    content = result.get("content", "")
    finding = _parse_finding(content)

    return AgentResult(
        agent_name=agent.name,
        division=agent.division,
        source_path=agent.source_path,
        status="completed" if result.get("success") else "offline_completed",
        mode=result.get("mode", "unknown"),
        success=result.get("success", False),
        finding=finding,
        raw_content=content,
        error=result.get("error"),
        started_at=started_at,
        completed_at=datetime.now().isoformat(),
    )
