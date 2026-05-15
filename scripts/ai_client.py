"""Shared AI client for MIFTEH OS GitHub-native workflows."""
import os
import json
from datetime import datetime, timezone

try:
    from openai import OpenAI
    _OPENAI_OK = True
except ImportError:
    _OPENAI_OK = False


def get_client():
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or not _OPENAI_OK:
        return None
    return OpenAI(api_key=key)


def generate_json(prompt_system, prompt_user, model="gpt-4o-mini", max_tokens=3000):
    """Call OpenAI and return (data, tokens_used, cost_usd, success)."""
    client = get_client()
    if not client:
        print("[ai_client] No OpenAI client — template fallback")
        return None, 0, 0.0, False

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user},
            ],
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        content = resp.choices[0].message.content
        usage = resp.usage
        input_t = usage.prompt_tokens if usage else 0
        output_t = usage.completion_tokens if usage else 0
        # gpt-4o-mini: $0.15/1M input, $0.60/1M output
        cost = (input_t * 0.15 + output_t * 0.60) / 1_000_000
        data = json.loads(content)
        print(f"[ai_client] Success — {input_t+output_t} tokens — ${cost:.6f}")
        return data, input_t + output_t, cost, True
    except Exception as exc:
        print(f"[ai_client] Failed: {exc}")
        return None, 0, 0.0, False


def generate_text(prompt_system, prompt_user, model="gpt-4o-mini", max_tokens=4500):
    """Call OpenAI and return (text, tokens_used, cost_usd, success) — for HTML/CSS/JS output."""
    client = get_client()
    if not client:
        print("[ai_client] No OpenAI client")
        return None, 0, 0.0, False
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": prompt_system},
                {"role": "user", "content": prompt_user},
            ],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        content = resp.choices[0].message.content.strip()
        # Strip markdown code fences if model wraps output
        if content.startswith("```"):
            lines = content.split("\n")
            end = -1 if (lines and lines[-1].strip() == "```") else len(lines)
            content = "\n".join(lines[1:end])
        usage = resp.usage
        in_t = usage.prompt_tokens if usage else 0
        out_t = usage.completion_tokens if usage else 0
        cost = (in_t * 0.15 + out_t * 0.60) / 1_000_000
        print(f"[ai_client] text: {in_t+out_t} tokens — ${cost:.6f}")
        return content, in_t + out_t, cost, True
    except Exception as exc:
        print(f"[ai_client] generate_text failed: {exc}")
        return None, 0, 0.0, False


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def timestamp_str():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
