"""Casos de uso da configuração de LLM: ler, atualizar e listar modelos."""
from __future__ import annotations

from ..infrastructure import llm, settings_repository
from ..infrastructure.llm.base import PROVIDERS, LLMConfig


class InvalidProvider(ValueError):
    pass


def get_settings() -> LLMConfig:
    return settings_repository.load_llm_config()


def update_settings(data: dict) -> LLMConfig:
    provider = data.get("provider")
    if provider is not None and provider not in PROVIDERS:
        raise InvalidProvider(f"Provedor inválido: {provider}. Use um de {PROVIDERS}.")
    return settings_repository.save_llm_config(data)


async def list_models(cfg: LLMConfig) -> list[str]:
    if cfg.provider not in PROVIDERS:
        raise InvalidProvider(f"Provedor inválido: {cfg.provider}.")
    return await llm.build_provider(cfg).list_models()
