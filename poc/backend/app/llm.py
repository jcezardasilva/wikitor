"""Cliente Ollama (provedor LLM local). Usado para gerar resumos/índices e Q&A."""
from __future__ import annotations

import json

import httpx

from . import config


class LLMError(RuntimeError):
    pass


async def generate(prompt: str, system: str | None = None, as_json: bool = False) -> str:
    """Chama /api/generate do Ollama (não-stream) e retorna o texto."""
    payload: dict = {
        "model": config.OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }
    if system:
        payload["system"] = system
    if as_json:
        payload["format"] = "json"

    try:
        async with httpx.AsyncClient(timeout=config.OLLAMA_TIMEOUT) as client:
            resp = await client.post(f"{config.OLLAMA_URL}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()
    except httpx.HTTPError as exc:
        raise LLMError(f"Falha ao chamar Ollama ({config.OLLAMA_MODEL}): {exc}") from exc


async def chat(messages: list[dict], system: str | None = None) -> str:
    """Chama /api/chat do Ollama (multi-turn, não-stream). `messages`: [{role, content}]."""
    msgs: list[dict] = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)
    payload = {
        "model": config.OLLAMA_MODEL,
        "messages": msgs,
        "stream": False,
        "options": {"temperature": 0.3},
    }
    try:
        async with httpx.AsyncClient(timeout=config.OLLAMA_TIMEOUT) as client:
            resp = await client.post(f"{config.OLLAMA_URL}/api/chat", json=payload)
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "").strip()
    except httpx.HTTPError as exc:
        raise LLMError(f"Falha ao chamar Ollama ({config.OLLAMA_MODEL}): {exc}") from exc


async def generate_json(prompt: str, system: str | None = None) -> dict:
    """Gera e parseia JSON; tolera cercas de código eventuais."""
    raw = await generate(prompt, system=system, as_json=True)
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise LLMError(f"Resposta não-JSON do LLM: {raw[:200]}")
