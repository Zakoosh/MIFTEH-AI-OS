"""Shared AI client for MIFTEH OS GitHub-native workflows.

Provider failover order: OpenAI gpt-4o-mini → Gemini 1.5 Flash → failure report.
Health state persisted in memory/provider_health.json.
"""
import os
import json
import time
import requests
from datetime import datetime, timezone
from pathlib import Path

try:
    from openai import OpenAI
    _OPENAI_OK = True
except ImportError:
    _OPENAI_OK = False

try:
    import google.generativeai as genai
    _GEMINI_OK = True
except ImportError:
    _GEMINI_OK = False

# ── constants ──────────────────────────────────────────────────────────────────
OPENAI_MODEL = "gpt-4o-mini"
GEMINI_MODEL = "gemini-1.5-flash"
# gpt-4o-mini pricing (per 1M tokens)
OPENAI_INPUT_COST  = 0.15
OPENAI_OUTPUT_COST = 0.60
# gemini-1.5-flash pricing (per 1M tokens, free tier / pay-as-you-go approx)
GEMINI_INPUT_COST  = 0.075
GEMINI_OUTPUT_COST = 0.30

HEALTH_FILE = Path("memory/provider_health.json")

# ── provider health ────────────────────────────────────────────────────────────

def _load_health() -> dict:
    if HEALTH_FILE.exists():
        try:
            return json.loads(HEALTH_FILE.read_text())
        except Exception:
            pass
    return {
        "openai":  {"status": "unknown", "failures": 0, "last_success": None, "last_failure": None},
        "gemini":  {"status": "unknown", "failures": 0, "last_success": None, "last_failure": None},
        "updated": None,
    }


def _save_health(h: dict):
    HEALTH_FILE.parent.mkdir(parents=True, exist_ok=True)
    h["updated"] = now_iso()
    HEALTH_FILE.write_text(json.dumps(h, indent=2))


def _mark_success(provider: str):
    h = _load_health()
    h[provider]["status"] = "healthy"
    h[provider]["failures"] = 0
    h[provider]["last_success"] = now_iso()
    _save_health(h)


def _mark_failure(provider: str, reason: str):
    h = _load_health()
    h[provider]["failures"] = h[provider].get("failures", 0) + 1
    h[provider]["last_failure"] = now_iso()
    fails = h[provider]["failures"]
    h[provider]["status"] = "critical" if fails >= 3 else "degraded"
    h[provider]["last_reason"] = reason[:200]
    _save_health(h)
    _send_provider_alert(provider, reason, fails)


def _send_provider_alert(provider: str, reason: str, fail_count: int):
    token = os.environ.get("TELEGRAM_LOG_TOKEN") or os.environ.get("TELEGRAM_ADMIN_LOG_TOKEN")
    chat  = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("TELEGRAM_ADMIN_CHAT_ID")
    if not token or not chat:
        return
    msg = (
        f"⚠️ <b>AI Provider Failure</b>\n"
        f"Provider: <code>{provider}</code>\n"
        f"Failures: {fail_count}\n"
        f"Reason: {reason[:300]}\n"
        f"Time: {now_iso()}"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": msg, "parse_mode": "HTML"},
            timeout=10,
        )
    except Exception:
        pass


# ── OpenAI ─────────────────────────────────────────────────────────────────────

def _openai_client():
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key or not _OPENAI_OK:
        return None
    return OpenAI(api_key=key)


def _openai_json(system: str, user: str, max_tokens: int):
    client = _openai_client()
    if not client:
        return None, 0, 0.0, False, "no_key"
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            temperature=0.7,
        )
        content = resp.choices[0].message.content
        usage = resp.usage
        in_t  = usage.prompt_tokens if usage else 0
        out_t = usage.completion_tokens if usage else 0
        cost  = (in_t * OPENAI_INPUT_COST + out_t * OPENAI_OUTPUT_COST) / 1_000_000
        data  = json.loads(content)
        _mark_success("openai")
        print(f"[ai_client/openai] {in_t+out_t} tokens — ${cost:.6f}")
        return data, in_t + out_t, cost, True, None
    except Exception as exc:
        err = str(exc)
        _mark_failure("openai", err)
        print(f"[ai_client/openai] failed: {err}")
        return None, 0, 0.0, False, err


def _openai_text(system: str, user: str, max_tokens: int):
    client = _openai_client()
    if not client:
        return None, 0, 0.0, False, "no_key"
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=0.3,
        )
        content = resp.choices[0].message.content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            end = -1 if (lines and lines[-1].strip() == "```") else len(lines)
            content = "\n".join(lines[1:end])
        usage = resp.usage
        in_t  = usage.prompt_tokens if usage else 0
        out_t = usage.completion_tokens if usage else 0
        cost  = (in_t * OPENAI_INPUT_COST + out_t * OPENAI_OUTPUT_COST) / 1_000_000
        _mark_success("openai")
        print(f"[ai_client/openai] text {in_t+out_t} tokens — ${cost:.6f}")
        return content, in_t + out_t, cost, True, None
    except Exception as exc:
        err = str(exc)
        _mark_failure("openai", err)
        print(f"[ai_client/openai] text failed: {err}")
        return None, 0, 0.0, False, err


# ── Gemini ─────────────────────────────────────────────────────────────────────

def _gemini_json(system: str, user: str, max_tokens: int):
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key or not _GEMINI_OK:
        return None, 0, 0.0, False, "no_key"
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=system,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.7,
                response_mime_type="application/json",
            ),
        )
        response = model.generate_content(user)
        content = response.text.strip()
        data = json.loads(content)
        # Gemini usage metadata
        usage = getattr(response, "usage_metadata", None)
        in_t  = getattr(usage, "prompt_token_count", 0) if usage else 0
        out_t = getattr(usage, "candidates_token_count", 0) if usage else 0
        cost  = (in_t * GEMINI_INPUT_COST + out_t * GEMINI_OUTPUT_COST) / 1_000_000
        _mark_success("gemini")
        print(f"[ai_client/gemini] {in_t+out_t} tokens — ${cost:.6f}")
        return data, in_t + out_t, cost, True, None
    except Exception as exc:
        err = str(exc)
        _mark_failure("gemini", err)
        print(f"[ai_client/gemini] failed: {err}")
        return None, 0, 0.0, False, err


def _gemini_text(system: str, user: str, max_tokens: int):
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key or not _GEMINI_OK:
        return None, 0, 0.0, False, "no_key"
    try:
        genai.configure(api_key=key)
        model = genai.GenerativeModel(
            GEMINI_MODEL,
            system_instruction=system,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=0.3,
            ),
        )
        response = model.generate_content(user)
        content = response.text.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            end = -1 if (lines and lines[-1].strip() == "```") else len(lines)
            content = "\n".join(lines[1:end])
        usage = getattr(response, "usage_metadata", None)
        in_t  = getattr(usage, "prompt_token_count", 0) if usage else 0
        out_t = getattr(usage, "candidates_token_count", 0) if usage else 0
        cost  = (in_t * GEMINI_INPUT_COST + out_t * GEMINI_OUTPUT_COST) / 1_000_000
        _mark_success("gemini")
        print(f"[ai_client/gemini] text {in_t+out_t} tokens — ${cost:.6f}")
        return content, in_t + out_t, cost, True, None
    except Exception as exc:
        err = str(exc)
        _mark_failure("gemini", err)
        print(f"[ai_client/gemini] text failed: {err}")
        return None, 0, 0.0, False, err


# ── failure report ─────────────────────────────────────────────────────────────

def _save_incident(kind: str, system: str, error_openai: str, error_gemini: str):
    inc_dir = Path("memory/incidents")
    inc_dir.mkdir(parents=True, exist_ok=True)
    ts = timestamp_str()
    inc = {
        "timestamp": now_iso(),
        "kind": kind,
        "prompt_system_preview": system[:100],
        "error_openai": error_openai,
        "error_gemini": error_gemini,
    }
    (inc_dir / f"{ts}.json").write_text(json.dumps(inc, indent=2))
    _send_provider_alert("ALL_PROVIDERS", f"OpenAI: {error_openai} | Gemini: {error_gemini}", 99)


# ── public API ─────────────────────────────────────────────────────────────────

def generate_json(prompt_system, prompt_user, model=None, max_tokens=3000):
    """OpenAI → Gemini failover. Returns (data, tokens, cost, success)."""
    data, tokens, cost, ok, err_oa = _openai_json(prompt_system, prompt_user, max_tokens)
    if ok:
        return data, tokens, cost, True

    print(f"[ai_client] OpenAI failed — trying Gemini")
    data, tokens, cost, ok, err_gm = _gemini_json(prompt_system, prompt_user, max_tokens)
    if ok:
        return data, tokens, cost, True

    _save_incident("generate_json", prompt_system, str(err_oa), str(err_gm))
    print(f"[ai_client] All providers failed for generate_json")
    return None, 0, 0.0, False


def generate_text(prompt_system, prompt_user, model=None, max_tokens=4500):
    """OpenAI → Gemini failover. Returns (text, tokens, cost, success)."""
    text, tokens, cost, ok, err_oa = _openai_text(prompt_system, prompt_user, max_tokens)
    if ok:
        return text, tokens, cost, True

    print(f"[ai_client] OpenAI failed — trying Gemini")
    text, tokens, cost, ok, err_gm = _gemini_text(prompt_system, prompt_user, max_tokens)
    if ok:
        return text, tokens, cost, True

    _save_incident("generate_text", prompt_system, str(err_oa), str(err_gm))
    print(f"[ai_client] All providers failed for generate_text")
    return None, 0, 0.0, False


def get_provider_health() -> dict:
    return _load_health()


# ── legacy alias ───────────────────────────────────────────────────────────────

def get_client():
    """Legacy: returns OpenAI client or None."""
    return _openai_client()


# ── time helpers ───────────────────────────────────────────────────────────────

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_str():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def timestamp_str():
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
