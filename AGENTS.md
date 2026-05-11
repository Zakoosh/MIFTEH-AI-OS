# AGENTS.md

## Cursor Cloud specific instructions

### Overview

MIFTEH AI OS is a centralized AI orchestration platform with:
- **Backend**: Python FastAPI server (`/workspace/backend/`) on port 8000
- **Frontend**: Static HTML/CSS/JS dashboard (`/workspace/frontend/dashboard/`) served on port 3000

No database — persistence is via JSON files in `backend/app/memory/reports/`.

### Running the backend

```bash
cd /workspace/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The `--reload` flag enables hot reloading for development. The server must be started from the `backend/` directory because report paths (`app/memory/reports/`) are relative.

### Running the frontend

```bash
cd /workspace/frontend/dashboard
python3 -m http.server 3000
```

The frontend fetches from `http://127.0.0.1:8000` — the backend must be running first.

### Key caveats

- **No test suite or linter config**: The project has no `pytest`, `pyproject.toml`, or linting configuration. Validate code with `python3 -m py_compile <file>` and import checks.
- **Missing core deps in `requirements.txt`**: The file does not include `fastapi`, `uvicorn`, `openai`, or `python-dotenv`, which are all required. Install them separately: `pip install fastapi uvicorn openai python-dotenv`.
- **Hardcoded Windows paths**: `app/core/projects.py`, `app/engine/agent_loader.py`, and `app/services/agency_indexer.py` reference `D:\Projects\...` paths. These external project/agent directories don't exist on Linux. Endpoints depending on them will return graceful errors.
- **OpenAI API key**: Optional. Without `OPENAI_API_KEY` in `backend/.env`, agent execution returns offline mock reports. The dashboard and all read endpoints work without it.
- **`.env` file**: Copy `backend/.env.example` to `backend/.env` before starting the backend.

## Agent System Rules

- Always reuse agents from `agency-agents-main`
- Never create random agents unless explicitly required
- Match missions to existing agent roles first
- Prefer specialized agents over generic execution
