from fastapi import APIRouter
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env_path = BASE_DIR / ".env"

load_dotenv(dotenv_path=env_path)

router = APIRouter()

api_key = os.getenv("OPENAI_API_KEY")

print("API KEY:", api_key)

client = OpenAI(api_key=api_key)


@router.get("/chat")
def chat():

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": "You are the core AI of MIFTEH AI OS."
            },
            {
                "role": "user",
                "content": "Say hello to MIFTEH AI OS"
            }
        ]
    )

    return {
        "response": response.choices[0].message.content
    }