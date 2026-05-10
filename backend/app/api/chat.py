from fastapi import APIRouter
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

router = APIRouter()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


@router.get("/chat")
def chat():
    return {
        "status": "disabled_for_now",
        "message": "Chat endpoint is ready, but OpenAI quota is currently unavailable."
    }
