"""Provedor Ollama (LLM local). Migrado do antigo ollama_client, comportamento inalterado."""
from __future__ import annotations

import httpx

from .base import LLMConfig, LLMError


class OllamaProvider:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg

    async def generate(self, prompt: str, system: str | None = None,
                       as_json: bool = False) -> str:
        payload: dict = {
            "model": self.cfg.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        if system:
            payload["system"] = system
        if as_json:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.cfg.timeout) as client:
                resp = await client.post(f"{self.cfg.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                return resp.json().get("response", "").strip()
        except httpx.HTTPError as exc:
            raise LLMError(f"Falha ao chamar Ollama ({self.cfg.model}): {exc}") from exc

    async def chat(self, messages: list[dict], system: str | None = None) -> str:
        msgs: list[dict] = []
        if system:
            msgs.append({"role": "system", "content": system})
        msgs.extend(messages)
        payload = {
            "model": self.cfg.model,
            "messages": msgs,
            "stream": False,
            "options": {"temperature": 0.3},
        }
        try:
            async with httpx.AsyncClient(timeout=self.cfg.timeout) as client:
                resp = await client.post(f"{self.cfg.base_url}/api/chat", json=payload)
                resp.raise_for_status()
                return resp.json().get("message", {}).get("content", "").strip()
        except httpx.HTTPError as exc:
            raise LLMError(f"Falha ao chamar Ollama ({self.cfg.model}): {exc}") from exc

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=self.cfg.timeout) as client:
                resp = await client.get(f"{self.cfg.base_url}/api/tags")
                resp.raise_for_status()
                models = resp.json().get("models", [])
                return [m["name"] for m in models if "name" in m]
        except httpx.HTTPError as exc:
            raise LLMError(f"Falha ao listar modelos do Ollama: {exc}") from exc
