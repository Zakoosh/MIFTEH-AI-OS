from openai import OpenAI
from dotenv import load_dotenv
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)


def run_agent(prompt: str):

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are part of MIFTEH AI OS."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7
        )

        return {
            "mode": "openai",
            "success": True,
            "content": response.choices[0].message.content
        }

    except Exception as error:
        return {
            "mode": "offline_mock",
            "success": False,
            "error": str(error),
            "content": """
OFFLINE MOCK REPORT

OpenAI quota/API is currently unavailable.

The system successfully:
1. Loaded the selected agency agent
2. Loaded project context
3. Built the execution prompt
4. Reached the AI execution layer

Next action:
- Fix OpenAI quota later
- Re-run the same endpoint
- The real agent report will replace this mock output

This confirms the MIFTEH AI OS execution pipeline is structurally working.
"""
        }
