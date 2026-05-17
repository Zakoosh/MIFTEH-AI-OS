from __future__ import annotations
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
_log = logging.getLogger("mifteh.startup")

_log.info("MIFTEH AI OS starting — Python %s", sys.version.split()[0])
_log.info("Working directory: %s", os.getcwd())

# Load env vars before any module-level API client initialization
from app.core.config import load_env as _load_env
_load_env()
_log.info("Environment loaded")

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.brain import router as brain_router
from app.api.agents import router as agents_router
from app.api.missions import router as missions_router
from app.api.registry import router as registry_router
from app.api.mission_engine import router as mission_engine_router
from app.api.git import router as git_router
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
from app.api.targets import router as targets_router
from app.api.adsense import router as adsense_router
from app.api.deployment import router as deployment_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    _log.info("Lifespan startup — initializing scheduler")
    from app.scheduler.loop_scheduler import get_scheduler
    scheduler = get_scheduler()
    try:
        await scheduler.start()
        from app.scheduler.loop_definitions import ALL_LOOPS
        _log.info("Scheduler started — %d loops registered", len(ALL_LOOPS))
    except Exception as exc:
        _log.error("Scheduler startup failed: %s", exc)
    _log.info("MIFTEH AI OS ready")
    yield
    _log.info("Lifespan shutdown — stopping scheduler")
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
app.include_router(targets_router)
app.include_router(adsense_router)
app.include_router(deployment_router)
app.include_router(chat_router)
app.include_router(brain_router)
app.include_router(agents_router)
app.include_router(mission_engine_router)
app.include_router(missions_router)
app.include_router(registry_router)
app.include_router(git_router)
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
    from app.scheduler.loop_scheduler import get_scheduler
    from app.scheduler.loop_definitions import ALL_LOOPS
    sched = get_scheduler()
    return {
        "status": "running",
        "system": "MIFTEH AI OS",
        "dashboard": "https://miftehos.com",
        "scheduler_running": sched._running,
        "loops_total": len(ALL_LOOPS),
    }
