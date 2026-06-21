"""Fluxo legado de turno único: a IA decide entre responder, autorar ou salvar.

Pré-Fase 0 (sem árvore de edição): um único documento em foco por vez.
"""
from __future__ import annotations

from ...domain.entities import Document
from ...infrastructure import document_repository
from .. import authoring_service, index_service, qa_service
from . import intent


async def _finalizar_e_salvar(messages: list[dict], contexto_doc: str | None,
                              doc_id: str | None) -> dict:
    draft = await authoring_service.coautoria_finalizar(messages, contexto_doc=contexto_doc)
    titulo, conteudo = draft["titulo"], draft["conteudo"]

    existing = document_repository.read_document(doc_id) if doc_id else None
    if existing:
        assunto, nivel, the_id = existing.assunto, existing.nivel, existing.id
    else:
        assunto, nivel = await intent.inferir_meta(titulo, conteudo)
        the_id = document_repository.new_doc_id(assunto, titulo)

    resumo = await index_service.gerar_resumo(titulo, conteudo)
    doc = Document(
        id=the_id, titulo=titulo, assunto=assunto, nivel=nivel,
        resumo=resumo, conteudo=conteudo, status="publicado",
    )
    document_repository.write_document(doc)
    index_service.rebuild_indices()
    verbo = "atualizado" if existing else "salvo"
    return {
        "acao": "salvo",
        "resposta": f"✅ Documento {verbo}: **{titulo}** (assunto: {assunto}, nível: {nivel}).",
        "doc": {"id": doc.id, "titulo": titulo},
    }


async def assistente(messages: list[dict], contexto_doc: str | None = None,
                     doc_id: str | None = None) -> dict:
    """Turno único do assistente. A IA decide entre responder, autorar ou salvar."""
    intencao = await intent.classificar_intencao(messages)

    if intencao == "salvar":
        return await _finalizar_e_salvar(messages, contexto_doc, doc_id)

    if intencao == "perguntar":
        pergunta = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        res = await qa_service.perguntar(pergunta)
        return {"acao": "resposta", "resposta": res["resposta"], "fontes": res["fontes"]}

    resposta = await authoring_service.coautoria_chat(messages, contexto_doc=contexto_doc)
    return {"acao": "autoria", "resposta": resposta}
