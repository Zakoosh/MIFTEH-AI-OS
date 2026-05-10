import os

AGENCY_PATH = r"D:\Projects\agency-agents-main"


def load_agent_file(agent_path: str):

    full_path = os.path.join(AGENCY_PATH, agent_path)

    if not os.path.exists(full_path):
        return {
            "error": "Agent file not found",
            "path": full_path
        }

    with open(full_path, "r", encoding="utf-8") as file:
        content = file.read()

    return {
        "path": full_path,
        "content": content
    }
