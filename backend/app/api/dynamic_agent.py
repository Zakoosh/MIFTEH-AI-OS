from fastapi import APIRouter, HTTPException
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os

from app.services.agent_loader import load_agent

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

router = APIRouter()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@router.get("/agent/run")
def run_agent(agent_path: str, prompt: str):
    agent_content = load_agent(agent_path)

    if agent_content is None:
        raise HTTPException(status_code=404, detail="Agent file not found")

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": agent_content
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    return {
        "agent_path": agent_path,
        "response": response.choices[0].message.content
    }
