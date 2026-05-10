from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.dynamic_agent import router as dynamic_agent_router
from app.api.projects import router as projects_router
from app.api.brain import router as brain_router

app = FastAPI(title="MIFTEH AI OS")

app.include_router(chat_router)
app.include_router(dynamic_agent_router)
app.include_router(projects_router)
app.include_router(brain_router)


@app.get("/")
def root():
    return {
        "status": "running",
        "system": "MIFTEH AI OS"
    }
