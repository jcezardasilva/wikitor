"""Persistência das settings de LLM em content/settings/llm.json.

Single-tenant: uma config global ativa. A api_key é gravada em claro no disco
(arquivo fora do git); a máscara para a API acontece na camada de presentation.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict

from . import config
from .llm.base import LLMConfig

_LLM_SETTINGS_FILE = "llm.json"


def mask_api_key(key: str | None) -> str | None:
    """Mascara a chave para exibição: mantém só os 4 últimos caracteres."""
    if not key:
        return None
    if len(key) <= 4:
        return "…" + key
    return "…" + key[-4:]


def _path():
    return config.SETTINGS_DIR / _LLM_SETTINGS_FILE


def _default() -> LLMConfig:
    """Default Ollama — compatibilidade retroativa quando não há config salva."""
    return LLMConfig(
        provider="ollama",
        base_url=config.OLLAMA_URL,
        model=config.OLLAMA_MODEL,
        api_key=None,
        timeout=config.OLLAMA_TIMEOUT,
    )


def load_llm_config() -> LLMConfig:
    """Lê a config ativa; se o arquivo não existir, retorna o default Ollama."""
    path = _path()
    if not path.exists():
        return _default()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return _default()
    base = _default()
    return LLMConfig(
        provider=data.get("provider", base.provider),
        base_url=data.get("base_url", base.base_url),
        model=data.get("model", base.model),
        api_key=data.get("api_key") or None,
        timeout=float(data.get("timeout", base.timeout)),
    )


def save_llm_config(data: dict) -> LLMConfig:
    """Mescla `data` sobre a config atual e grava de forma atômica.

    Regra de segurança: `api_key` vazia/ausente em `data` mantém a chave atual
    (nunca sobrescreve um segredo existente com vazio).
    """
    current = load_llm_config()
    merged = asdict(current)
    for key in ("provider", "base_url", "model", "timeout"):
        if data.get(key) is not None:
            merged[key] = data[key]
    new_key = data.get("api_key")
    if new_key:  # só troca se vier valor não-vazio
        merged["api_key"] = new_key

    config.SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    path = _path()
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)  # escrita atômica
    return load_llm_config()
