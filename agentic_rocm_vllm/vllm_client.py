"""
Thin wrapper around an OpenAI-compatible vLLM server.

vLLM exposes an OpenAI-compatible REST API, so we talk to it with the
standard `openai` Python SDK (or raw httpx if the SDK is unavailable).
This is what lets the AMD lab's locally-hosted model power the agent
without any cloud dependency.
"""
from __future__ import annotations
import logging
from typing import List, Dict

from . import config

logger = logging.getLogger("agentic_rocm_vllm.client")


class VLLMUnavailable(RuntimeError):
    """Raised when the vLLM server cannot be reached."""


def _chat_via_openai_sdk(messages: List[Dict[str, str]]) -> str:
    from openai import OpenAI  # imported lazily so the dep is optional

    client = OpenAI(
        base_url=config.VLLM_BASE_URL,
        api_key=config.VLLM_API_KEY,
        timeout=config.REQUEST_TIMEOUT_S,
    )
    resp = client.chat.completions.create(
        model=config.VLLM_MODEL,
        messages=messages,
        max_tokens=config.MAX_TOKENS,
        temperature=config.TEMPERATURE,
    )
    return resp.choices[0].message.content or ""


def _chat_via_httpx(messages: List[Dict[str, str]]) -> str:
    import httpx

    url = f"{config.VLLM_BASE_URL.rstrip('/')}/chat/completions"
    payload = {
        "model": config.VLLM_MODEL,
        "messages": messages,
        "max_tokens": config.MAX_TOKENS,
        "temperature": config.TEMPERATURE,
    }
    headers = {"Authorization": f"Bearer {config.VLLM_API_KEY}"}
    with httpx.Client(timeout=config.REQUEST_TIMEOUT_S) as client:
        r = client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
    return data["choices"][0]["message"]["content"]


def chat(messages: List[Dict[str, str]]) -> str:
    """
    Send a chat completion request to vLLM and return the text content.

    Tries the official OpenAI SDK first, then falls back to httpx so the
    module works with whichever dependency is already installed in the lab.
    """
    try:
        try:
            return _chat_via_openai_sdk(messages)
        except ModuleNotFoundError:
            return _chat_via_httpx(messages)
    except Exception as exc:  # noqa: BLE001 - surfaced as a typed error
        logger.warning("vLLM request failed: %s", exc)
        raise VLLMUnavailable(str(exc)) from exc


def health_check() -> bool:
    """Return True if the vLLM server answers the /models endpoint."""
    try:
        import httpx

        url = f"{config.VLLM_BASE_URL.rstrip('/')}/models"
        with httpx.Client(timeout=5.0) as client:
            r = client.get(url, headers={"Authorization": f"Bearer {config.VLLM_API_KEY}"})
            return r.status_code == 200
    except Exception:  # noqa: BLE001
        return False
