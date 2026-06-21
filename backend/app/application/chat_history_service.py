"""Caso de uso: registrar o histórico de interações do assistente.

Cada sessão (mantida pelo cliente entre turnos via `session_id`) gera um arquivo próprio
em `content/chats/`, no mesmo espírito dos documentos da wiki — para depois servir de
insumo a revisão de processos, novas funcionalidades e seções de artigo.
"""
from __future__ import annotations

import uuid

from ..infrastructure import chat_repository


def novo_session_id() -> str:
    return uuid.uuid4().hex


def registrar_turno(session_id: str | None, mensagens: list[dict], resposta: str) -> str:
    """Grava o turno (histórico do cliente + resposta do assistente) e retorna o session_id."""
    sid = session_id or novo_session_id()
    transcricao = [*mensagens, {"role": "assistant", "content": resposta}]
    chat_repository.write_session(sid, transcricao)
    return sid
