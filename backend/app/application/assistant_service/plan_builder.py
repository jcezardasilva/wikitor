"""Construção do plano de gravação (`SavePlan`) a partir da árvore de edição.

A guarda de afinidade (`document_repository.affinity_target`) decide o destino final de
cada item — nunca sobrescreve um arquivo de outro assunto.
"""
from __future__ import annotations

from ...domain.entities import EditNodeIn, SavePlan, SavePlanItem
from ...infrastructure import document_repository
from .. import authoring_service
from . import intent


def nos_alterados(arvore: list[EditNodeIn]) -> list[EditNodeIn]:
    """Só os nós que mudaram: alterados, ou novos (sem doc_id) com conteúdo."""
    return [n for n in arvore if n.alterado or (n.doc_id is None and n.conteudo.strip())]


async def item_plano(node: EditNodeIn, messages: list[dict]) -> SavePlanItem:
    # O conteúdo é sintetizado da conversa por nó (como no fluxo legado), com o texto
    # atual do nó como contexto; a afinidade então decide o destino.
    draft = await authoring_service.coautoria_finalizar(
        messages, contexto_doc=node.conteudo or None
    )
    conteudo = draft["conteudo"]
    titulo = node.titulo or draft["titulo"]
    assunto_inferido, nivel = await intent.inferir_meta(titulo, conteudo)
    assunto = assunto_inferido or node.assunto or "geral"
    final_id, tipo, redirecionado = document_repository.affinity_target(
        assunto, node.doc_id, titulo
    )
    return SavePlanItem(
        node_id=node.node_id,
        assunto=assunto,
        doc_id=node.doc_id,
        arquivo=f"docs/{final_id}.md",
        titulo=titulo,
        nivel=node.nivel or nivel,
        tipo=tipo,
        redirecionado=redirecionado,
        conteudo=conteudo,
    )


def plano_remocao(node: EditNodeIn, acao: str) -> dict:
    item = SavePlanItem(
        node_id=node.node_id, assunto=node.assunto, doc_id=node.doc_id,
        arquivo=f"docs/{node.doc_id}.md", titulo=node.titulo, nivel=node.nivel,
        tipo=acao, redirecionado=False, conteudo="",
    )
    plano = SavePlan(itens=[item])
    verbo = "remover (excluir)" if acao == "remover" else "arquivar"
    return {
        "acao": "plano_save",
        "resposta": f"Vou {verbo}: docs/{node.doc_id}.md\n\nConfirma?",
        "plano": plano.model_dump(),
    }


def descreve_plano(plano: SavePlan) -> str:
    if not plano.itens:
        return "Não há alterações para gravar."
    linhas = []
    for it in plano.itens:
        marca = " (redirecionado p/ afinidade)" if it.redirecionado else ""
        linhas.append(f"- {it.arquivo} — {it.tipo}{marca}")
    corpo = "\n".join(linhas)
    return f"Vou gravar:\n{corpo}\n\nConfirma?"


async def propor_plano(arvore: list[EditNodeIn], messages: list[dict]) -> dict:
    itens = [await item_plano(n, messages) for n in nos_alterados(arvore)]
    plano = SavePlan(itens=itens)
    return {"acao": "plano_save", "resposta": descreve_plano(plano), "plano": plano.model_dump()}
