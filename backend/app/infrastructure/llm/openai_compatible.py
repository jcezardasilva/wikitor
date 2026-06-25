"""Provedor genérico OpenAI-compatible (Groq, OpenRouter, LM Studio, vLLM, ...).

Fala o dialeto /v1 da OpenAI via httpx; `base_url` é guardada sem o sufixo /v1.
"""
from __future__ import annotations

import httpx

from .base import LLMConfig, LLMError


class OpenAICompatibleProvider:
    def __init__(self, cfg: LLMConfig):
        self.cfg = cfg

    def _headers(self) -> dict:
        if self.cfg.api_key:
            return {"Authorization": f"Bearer {self.cfg.api_key}"}
        return {}

    async def _chat_completion(self, messages: list[dict], temperature: float,
                               as_json: bool = False) -> str:
        body: dict = {
            "model": self.cfg.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        if as_json:
            body["response_format"] = {"type": "json_object"}
        try:
            async with httpx.AsyncClient(timeout=self.cfg.timeout) as client:
                resp = await client.post(
                    f"{self.cfg.base_url}/v1/chat/completions",
                    json=body, headers=self._headers(),
                )
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPError as exc:
            raise LLMError(
                f"Falha ao chamar provedor OpenAI-compatible ({self.cfg.model}): {exc}"
            ) from exc
        except (KeyError, IndexError) as exc:
            raise LLMError(f"Resposta inesperada do provedor OpenAI-compatible: {exc}") from exc

    async def generate(self, prompt: str, system: str | None = None,
                       as_json: bool = False) -> str:
        messages = ([{"role": "system", "content": system}] if system else []) \
            + [{"role": "user", "content": prompt}]
        return await self._chat_completion(messages, temperature=0.2, as_json=as_json)

    async def chat(self, messages: list[dict], system: str | None = None) -> str:
        msgs = ([{"role": "system", "content": system}] if system else []) + list(messages)
        return await self._chat_completion(msgs, temperature=0.3)

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=self.cfg.timeout) as client:
                resp = await client.get(f"{self.cfg.base_url}/v1/models", headers=self._headers())
                resp.raise_for_status()
                data = resp.json().get("data", [])
                return [d["id"] for d in data if "id" in d]
        except httpx.HTTPError as exc:
            raise LLMError(f"Falha ao listar modelos do provedor: {exc}") from exc
