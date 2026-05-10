from app.brain.agent_matcher import match_agents_for_project


def build_workflow_preview(project_id: str):

    match_data = match_agents_for_project(project_id)

    if "error" in match_data:
        return match_data

    project_name = match_data["project"]
    project_type = match_data["type"]
    workflow = match_data["workflow"]

    run_plan = []

    for phase in workflow:
        phase_agents = []

        for agent in phase["agents"]:
            phase_agents.append({
                "agent": agent["name"],
                "division": agent["division"],
                "agent_path": agent["path"],
                "instruction": build_instruction(project_name, project_type, phase["name"], agent["name"])
            })

        run_plan.append({
            "step": phase["step"],
            "phase": phase["name"],
            "agents": phase_agents
        })

    return {
        "project": project_name,
        "project_id": project_id,
        "type": project_type,
        "mode": "preview_only",
        "note": "This does not call OpenAI yet. It prepares execution instructions using agency-agents-main.",
        "run_plan": run_plan
    }


def build_instruction(project_name: str, project_type: str, phase_name: str, agent_name: str):

    return f'''
You are {agent_name} from agency-agents-main.

Project: {project_name}
Project Type: {project_type}
Workflow Phase: {phase_name}

Your task:
- Review the project context
- Apply your original agency agent role
- Produce practical recommendations
- Focus only on your specialty
- Return clear action items
- Avoid generic advice
'''
