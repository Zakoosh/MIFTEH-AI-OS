import json
from app.engine.agent_loader import load_agent_file
from app.brain.context_builder import build_project_context


def build_agent_prompt(project_id: str, agent_data: dict):

    context = build_project_context(project_id)

    loaded_agent = load_agent_file(agent_data["path"])

    if "error" in loaded_agent:
        return loaded_agent

    prompt = f'''
You are an AI specialist agent from agency-agents-main.

=== AGENT FILE ===
{loaded_agent["content"]}

=== PROJECT CONTEXT ===
{json.dumps(context, indent=2)}

=== YOUR TASK ===
Review the project carefully.

Return:
1. Problems
2. Improvements
3. Action Plan
4. Technical Recommendations
5. Priority Tasks

Be direct and practical.
'''

    return {
        "project_id": project_id,
        "agent": agent_data["name"],
        "division": agent_data["division"],
        "prompt": prompt
    }
