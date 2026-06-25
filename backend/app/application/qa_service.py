"""Q&A por navegação na cadeia de índices.

NÃO usa busca vetorial — segue o design: o LLM lê os índices (resumos + paths),
escolhe os documentos relevantes e responde com base no markdown completo, citando as fontes.
"""
from __future__ import annotations

from ..infrastructure import document_repository, index_repository, llm

_PICK_SYSTEM = (
    "Você seleciona documentos relevantes para responder uma pergunta. "
    "Receberá um índice (lista de documentos com id, titulo, resumo e nivel). "
    "Responda em JSON: {\"ids\": [...]} com os ids dos documentos mais relevantes (no máx. 4). "
    "Se nenhum for relevante, retorne lista vazia."
)

_ANSWER_SYSTEM = (
    "Você responde perguntas usando APENAS o conteúdo fornecido dos documentos da wiki, "
    "em português do Brasil. Cite as fontes pelo título. "
    "Se o conteúdo não cobrir a pergunta, diga claramente que não há informação na wiki."
)


def _flatten_index() -> list[dict]:
    """Lê _master.json → {assunto}.json e devolve entradas achatadas (sem abrir os docs)."""
    master = index_repository.read_index("_master") or {"assuntos": []}
    entradas: list[dict] = []
    for a in master.get("assuntos", []):
        subj = index_repository.read_index(a["assunto"])
        if not subj:
            continue
        for nivel, items in subj.get("niveis", {}).items():
            for it in items:
                entradas.append(
                    {"id": it["id"], "titulo": it["titulo"],
                     "resumo": it["resumo"], "nivel": nivel, "assunto": a["assunto"]}
                )
    return entradas


async def perguntar(pergunta: str) -> dict:
    entradas = _flatten_index()
    if not entradas:
        return {"resposta": "A wiki ainda não tem conteúdo indexado.", "fontes": []}

    # Etapa 1 — navegar o índice: LLM escolhe documentos relevantes.
    catalogo = "\n".join(
        f"- id={e['id']} | [{e['nivel']}] {e['titulo']}: {e['resumo']}" for e in entradas
    )
    pick = await llm.generate_json(
        f"Índice da wiki:\n{catalogo}\n\nPergunta: {pergunta}",
        system=_PICK_SYSTEM,
    )
    ids = [i for i in pick.get("ids", []) if any(e["id"] == i for e in entradas)][:4]

    # Etapa 2 — carregar markdown completo dos escolhidos.
    fontes = []
    contexto_blocos = []
    for doc_id in ids:
        doc = document_repository.read_document(doc_id)
        if doc:
            fontes.append({"id": doc.id, "titulo": doc.titulo})
            contexto_blocos.append(f"## {doc.titulo}\n{doc.conteudo}")

    if not contexto_blocos:
        return {"resposta": "Não encontrei documentos relevantes na wiki para essa pergunta.",
                "fontes": []}

    # Etapa 3 — responder com base no conteúdo.
    contexto = "\n\n---\n\n".join(contexto_blocos)
    resposta = await llm.generate(
        f"Documentos:\n{contexto}\n\nPergunta: {pergunta}\n\nResposta:",
        system=_ANSWER_SYSTEM,
    )
    return {"resposta": resposta, "fontes": fontes}
