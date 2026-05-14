from __future__ import annotations
# Load env vars before any module-level API client initialization
from app.core.config import load_env as _load_env
_load_env()

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.brain import router as brain_router
from app.api.agents import router as agents_router
from app.api.missions import router as missions_router
from app.api.apply import router as apply_router
from app.api.autonomy import router as autonomy_router
from app.api.collaboration import router as collaboration_router
from app.api.workgen import router as workgen_router
from app.api.planning import router as planning_router
from app.api.delivery import router as delivery_router
from app.api.repository_automation import router as repo_router
from app.api.cicd import router as cicd_router
from app.api.providers import router as providers_router
from app.api.runtime import router as runtime_router
from app.api.operations import router as operations_router
from app.api.dashboard import router as dashboard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.scheduler.loop_scheduler import get_scheduler
    scheduler = get_scheduler()
    await scheduler.start()
    yield
    await scheduler.stop()


app = FastAPI(title="MIFTEH AI OS", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://miftehos.com",
        "http://miftehos.com",
        "https://www.miftehos.com",
        "https://yallaplays.com",
        "http://localhost:3000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Cookie", "X-OS-Token", "X-Admin-Token"],
    expose_headers=["Set-Cookie"],
)

app.include_router(dashboard_router)
app.include_router(chat_router)
app.include_router(brain_router)
app.include_router(agents_router)
app.include_router(missions_router)
app.include_router(apply_router)
app.include_router(autonomy_router)
app.include_router(collaboration_router)
app.include_router(workgen_router)
app.include_router(planning_router)
app.include_router(delivery_router)
app.include_router(repo_router)
app.include_router(cicd_router)
app.include_router(providers_router)
app.include_router(runtime_router)
app.include_router(operations_router)


@app.get("/health")
def health():
    return {
        "status": "running",
        "system": "MIFTEH AI OS",
        "dashboard": "https://miftehos.com",
    }
