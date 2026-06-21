"""Casos de uso de gravação/ciclo de vida do documento.

A guarda de afinidade (`document_repository.affinity_target`) garante que conteúdo do
assunto A nunca sobrescreve um arquivo sob o assunto B — corrige o bug de sobrescrita.
"""
from __future__ import annotations

from ..domain.entities import Document, SavePlan, SavePlanItem, slugify
from ..infrastructure import config, document_repository, index_repository
from . import index_service


def get_master_index() -> dict:
    return index_repository.read_index("_master") or {"assuntos": []}


def get_subject_index(assunto: str) -> dict | None:
    return index_repository.read_index(assunto)


def get_document(doc_id: str) -> Document | None:
    return document_repository.read_document(doc_id)


async def save_document(
    titulo: str, assunto: str, conteudo: str, nivel: str,
    doc_id: str | None, gerar_resumo: bool,
) -> Document:
    """Cria/atualiza um documento isolado (fluxo legado de save manual) e reindexa."""
    nivel_valido = nivel if nivel in config.NIVEIS else "iniciante"
    final_id = doc_id or document_repository.new_doc_id(assunto, titulo)

    resumo = ""
    if gerar_resumo:
        resumo = await index_service.gerar_resumo(titulo, conteudo)

    doc = Document(
        id=final_id,
        titulo=titulo,
        assunto=slugify(assunto),
        nivel=nivel_valido,
        resumo=resumo,
        conteudo=conteudo,
        status="publicado",
    )
    document_repository.write_document(doc)
    index_service.rebuild_indices()
    return doc


async def apply_plan_item(item: SavePlanItem) -> dict:
    """Aplica um item do plano. Tipos: novo/atualiza (grava), remover (apaga), arquivar."""
    if item.tipo == "remover" and item.doc_id:
        document_repository.trash_document(item.doc_id)  # excluir = mover p/ lixeira
        return {"node_id": item.node_id, "id": item.doc_id, "tipo": "lixeira"}
    if item.tipo == "arquivar" and item.doc_id:
        document_repository.set_status(item.doc_id, "arquivado")
        return {"node_id": item.node_id, "id": item.doc_id, "tipo": "arquivado"}

    # novo/atualiza — guarda de afinidade decide o destino.
    doc_id, _tipo, _redir = document_repository.affinity_target(
        item.assunto, item.doc_id, item.titulo
    )
    nivel = item.nivel if item.nivel in config.NIVEIS else "iniciante"
    resumo = await index_service.gerar_resumo(item.titulo, item.conteudo)
    doc = Document(
        id=doc_id, titulo=item.titulo, assunto=slugify(item.assunto),
        nivel=nivel, resumo=resumo, conteudo=item.conteudo, status="publicado",
    )
    document_repository.write_document(doc)
    return {"node_id": item.node_id, "id": doc.id, "assunto": doc.assunto,
            "titulo": doc.titulo, "tipo": "salvo"}


async def commit_plan(plano: SavePlan) -> list[dict]:
    """Grava o plano confirmado. Único caso de uso que escreve/remove no modo árvore."""
    salvos = [await apply_plan_item(item) for item in plano.itens]
    index_service.rebuild_indices()
    return salvos


def archive_document(doc_id: str) -> Document | None:
    """Arquiva: sai do índice, mas o arquivo permanece no lugar (reversível)."""
    doc = document_repository.set_status(doc_id, "arquivado")
    if doc is not None:
        index_service.rebuild_indices()
    return doc


def restore_archived(doc_id: str) -> Document | None:
    """Restaura um documento arquivado (status volta a 'publicado')."""
    doc = document_repository.set_status(doc_id, "publicado")
    if doc is not None:
        index_service.rebuild_indices()
    return doc


def trash_document(doc_id: str) -> Document | None:
    """Excluir = mover para a lixeira (recuperável; purge só após a retenção)."""
    doc = document_repository.trash_document(doc_id)
    if doc is not None:
        index_service.rebuild_indices()
    return doc


def list_trash() -> dict:
    """Lista os documentos na lixeira com os dias restantes até poder excluir de vez."""
    itens = []
    for doc in document_repository.list_trash():
        dias = document_repository.dias_na_lixeira(doc)
        restante = max(0, config.TRASH_RETENTION_DAYS - dias)
        itens.append({
            "id": doc.id, "titulo": doc.titulo, "assunto": doc.assunto,
            "excluido_em": doc.excluido_em, "dias": dias, "restante": restante,
            "elegivel": restante == 0,
        })
    return {"itens": itens, "retencao_dias": config.TRASH_RETENTION_DAYS}


def restore_from_trash(doc_id: str) -> Document | None:
    """Restaura um documento da lixeira de volta ao acervo."""
    doc = document_repository.restore_from_trash(doc_id)
    if doc is not None:
        index_service.rebuild_indices()
    return doc


def purge_document(doc_id: str) -> str:
    """Exclusão definitiva. Só permitida após a retenção (30 dias) na lixeira."""
    return document_repository.purge_document(doc_id)
