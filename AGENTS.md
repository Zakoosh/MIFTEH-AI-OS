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

Current persistence layer uses JSON reports.
Future roadmap may include SQLite or PostgreSQL.

## AI Provider Strategy

Priority order:
1. OpenAI
2. Gemini
3. Offline mock mode

If providers fail:
- Save report
- Return graceful fallback response
- Keep pipeline operational


## Report Rules

All agents should generate structured reports.

Reports should include:
- Summary
- Findings
- Risks
- Suggested actions
- Priority level



## Mission Workflow

Standard execution flow:

1. Scan project
2. Detect issues
3. Match suitable agents
4. Generate reports
5. Generate safe actions
6. Preview changes
7. Apply approved changes
8. Save reports


## Active Projects

### MIFTEH AI OS
AI orchestration platform.

### YallaPlays
HTML5 gaming platform focused on SEO, performance, and monetization.

### Fionera
Finance and investment dashboard focused on analytics, charts, and security.


## Safe File Modification Rules

- Prefer `replace_in_file` operations over rewriting full files
- Never modify `.env` files
- Never expose secrets, API keys, or tokens
- Never delete important project files automatically
- Always preview risky changes before applying


## Automation Goal

The long-term goal is continuous autonomous project improvement.

Agents should:
- Monitor projects continuously
- Detect improvements automatically
- Suggest safe code changes
- Improve performance and security
- Assist with UI/UX improvements
- Generate actionable implementation tasks
