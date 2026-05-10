from pathlib import Path

AGENTS_PATH = Path(r"D:\Projects\agency-agents-main")


def load_agent(agent_path: str):
    full_path = AGENTS_PATH / agent_path

    if not full_path.exists():
        return None

    with open(full_path, "r", encoding="utf-8") as file:
        return file.read()
