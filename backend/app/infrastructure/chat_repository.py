"""Persistência de sessões de chat (histórico de interações), uma por arquivo.

Layout:
    content/chats/{session_id}.md      # frontmatter + transcrição em markdown

O cliente reenvia o histórico completo (`messages`) a cada turno — não há diffing:
a cada turno a sessão é regravada por completo com a transcrição até aqui.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from . import config, frontmatter


def _session_path(session_id: str) -> Path:
    return config.CHATS_DIR / f"{session_id}.md"


def _transcrever(mensagens: list[dict]) -> str:
    blocos = []
    for m in mensagens:
        titulo = "Usuário" if m["role"] == "user" else "Assistente"
        blocos.append(f"## {titulo}\n\n{m['content'].strip()}")
    return "\n\n".join(blocos) + "\n"


def read_session_meta(session_id: str) -> dict | None:
    path = _session_path(session_id)
    if not path.exists():
        return None
    meta, _ = frontmatter.parse(path.read_text(encoding="utf-8"))
    return meta


def write_session(session_id: str, mensagens: list[dict]) -> None:
    """Regrava a sessão por completo a partir da transcrição atual (até este turno)."""
    existente = read_session_meta(session_id)
    criado_em = existente.get("criado_em") if existente else None

    meta = {
        "id": session_id,
        "criado_em": criado_em or date.today().isoformat(),
        "atualizado_em": date.today().isoformat(),
        "total_mensagens": len(mensagens),
    }
    path = _session_path(session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter.dump(meta, _transcrever(mensagens)), encoding="utf-8")
