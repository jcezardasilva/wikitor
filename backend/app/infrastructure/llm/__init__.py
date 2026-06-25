"""Facade do LLM. Os serviços importam este módulo e ignoram qual provedor está ativo.

Mantém as mesmas assinaturas do antigo `ollama_client` (generate/chat/generate_json
+ LLMError) para que o refactor dos serviços seja só a troca do import.
"""
from __future__ import annotations

import json

from .base import LLMConfig, LLMError, LLMProvider
from .ollama import OllamaProvider
from .openai_compatible import OpenAICompatibleProvider

__all__ = ["LLMError", "LLMConfig", "LLMProvider", "build_provider",
           "generate", "chat", "generate_json"]


def build_provider(cfg: LLMConfig) -> LLMProvider:
    """Instancia o provedor concreto a partir da config."""
    if cfg.provider == "openai_compatible":
        return OpenAICompatibleProvider(cfg)
    return OllamaProvider(cfg)


def _active() -> LLMProvider:
    # Import tardio evita ciclo (settings_repository importa de .base).
    from .. import settings_repository
    return build_provider(settings_repository.load_llm_config())


async def generate(prompt: str, system: str | None = None, as_json: bool = False) -> str:
    return await _active().generate(prompt, system=system, as_json=as_json)


async def chat(messages: list[dict], system: str | None = None) -> str:
    return await _active().chat(messages, system=system)


async def generate_json(prompt: str, system: str | None = None) -> dict:
    """Gera e parseia JSON; tolera cercas de código eventuais.

    Lógica única, reaproveitada por qualquer provedor.
    """
    raw = (await generate(prompt, system=system, as_json=True)).strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw[raw.find("{"):]
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        start, end = raw.find("{"), raw.rfind("}")
        if start >= 0 and end > start:
            return json.loads(raw[start:end + 1])
        raise LLMError(f"Resposta não-JSON do LLM: {raw[:200]}") from None
