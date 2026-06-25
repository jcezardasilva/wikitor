"""Contrato comum aos provedores de LLM (Ollama, OpenAI-compatible, ...)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

# Provedores suportados. Único lugar que enumera os valores válidos.
PROVIDERS = ("ollama", "openai_compatible")


class LLMError(RuntimeError):
    """Falha ao chamar um provedor de LLM (rede, credencial, resposta inválida)."""


@dataclass(frozen=True)
class LLMConfig:
    """Configuração ativa do provedor. `api_key` em claro só vive em memória."""
    provider: str
    base_url: str
    model: str
    api_key: str | None = None
    timeout: float = 120.0


@runtime_checkable
class LLMProvider(Protocol):
    """Interface que todo provedor concreto implementa."""

    async def generate(self, prompt: str, system: str | None = None,
                       as_json: bool = False) -> str: ...

    async def chat(self, messages: list[dict], system: str | None = None) -> str: ...

    async def list_models(self) -> list[str]: ...
