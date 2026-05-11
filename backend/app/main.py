from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.brain import router as brain_router
from app.api.agents import router as agents_router
from app.api.missions import router as missions_router
from app.api.registry import router as registry_router
from app.api.mission_engine import router as mission_engine_router
from app.api.intelligence import router as intelligence_router

app = FastAPI(title="MIFTEH AI OS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(brain_router)
app.include_router(agents_router)
app.include_router(mission_engine_router)
app.include_router(missions_router)
app.include_router(registry_router)
app.include_router(intelligence_router)


@app.get("/")
def root():
    return {
        "status": "running",
        "system": "MIFTEH AI OS"
    }
