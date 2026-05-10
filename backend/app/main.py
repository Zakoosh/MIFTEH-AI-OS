from fastapi import FastAPI

from app.api.chat import router as chat_router
from app.api.brain import router as brain_router
from app.api.agents import router as agents_router

app = FastAPI()

app.include_router(chat_router)
app.include_router(brain_router)
app.include_router(agents_router)


@app.get("/")
def root():
    return {
        "status": "running",
        "system": "MIFTEH AI OS"
    }