"""Wikitor — POC. Backend FastAPI: markdown local + Ollama, sem auth/Azure."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import ai, config, indexer, storage
from .models import (
    AssistantRequest,
    CommitRequest,
    Document,
    SaveDocRequest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.ensure_dirs()
    indexer.rebuild_indices()  # garante índices consistentes ao subir
    yield


app = FastAPI(title="Wikitor POC", lifespan=lifespan)


# ---------- API: navegação / consulta ----------

@app.get("/api/index")
def get_master_index():
    return storage.read_index("_master") or {"assuntos": []}


@app.get("/api/subjects/{assunto}")
def get_subject_index(assunto: str):
    idx = storage.read_index(assunto)
    if idx is None:
        raise HTTPException(404, "Assunto não encontrado")
    return idx


@app.get("/api/docs/{doc_id:path}")
def get_document(doc_id: str):
    doc = storage.read_document(doc_id)
    if doc is None:
        raise HTTPException(404, "Documento não encontrado")
    return doc


# ---------- API: atualização manual ----------

@app.post("/api/docs")
async def save_document(req: SaveDocRequest):
    nivel = req.nivel if req.nivel in config.NIVEIS else "iniciante"
    doc_id = req.id or storage.new_doc_id(req.assunto, req.titulo)

    resumo = ""
    if req.gerar_resumo:
        resumo = await indexer.gerar_resumo(req.titulo, req.conteudo)

    doc = Document(
        id=doc_id,
        titulo=req.titulo,
        assunto=storage.slugify(req.assunto),
        nivel=nivel,
        resumo=resumo,
        conteudo=req.conteudo,
        status="publicado",
    )
    storage.write_document(doc)
    indexer.rebuild_indices()
    return doc


# ---------- API: assistente unificado (responder / autorar / salvar) ----------

@app.post("/api/ai/assistant")
async def ai_assistant(req: AssistantRequest):
    """Turno único do assistente. A IA infere a intenção a partir da conversa.

    Modo árvore (Fase 0): se `arvore`/`plano_pendente`/`proposta_pendente` vierem, usa o
    fluxo ciente da árvore (propõe plano, nunca grava). Senão, mantém o fluxo legado.
    """
    msgs = [m.model_dump() for m in req.messages]
    if req.modo == "arvore" or req.arvore or req.plano_pendente or req.proposta_pendente:
        return await ai.assistente_arvore(
            msgs, req.arvore, req.foco, req.plano_pendente, req.proposta_pendente
        )
    return await ai.assistente(msgs, contexto_doc=req.contexto_doc, doc_id=req.doc_id)


async def _aplicar_item(item) -> dict:
    """Aplica um item do plano. Tipos: novo/atualiza (grava), remover (apaga), arquivar."""
    if item.tipo == "remover" and item.doc_id:
        storage.trash_document(item.doc_id)  # excluir = mover para a lixeira
        return {"node_id": item.node_id, "id": item.doc_id, "tipo": "lixeira"}
    if item.tipo == "arquivar" and item.doc_id:
        storage.set_status(item.doc_id, "arquivado")
        return {"node_id": item.node_id, "id": item.doc_id, "tipo": "arquivado"}

    # novo/atualiza — guarda de afinidade decide o destino.
    doc_id, _tipo, _redir = storage.affinity_target(item.assunto, item.doc_id, item.titulo)
    nivel = item.nivel if item.nivel in config.NIVEIS else "iniciante"
    resumo = await indexer.gerar_resumo(item.titulo, item.conteudo)
    doc = Document(
        id=doc_id, titulo=item.titulo, assunto=storage.slugify(item.assunto),
        nivel=nivel, resumo=resumo, conteudo=item.conteudo, status="publicado",
    )
    storage.write_document(doc)
    return {"node_id": item.node_id, "id": doc.id, "assunto": doc.assunto,
            "titulo": doc.titulo, "tipo": "salvo"}


@app.post("/api/docs/commit")
async def commit_plan(req: CommitRequest):
    """Grava o plano confirmado. Única rota que escreve/remove no modo árvore.

    A guarda de afinidade (`storage.affinity_target`) garante que conteúdo do assunto A
    nunca sobrescreve um arquivo sob o assunto B — corrige o bug de sobrescrita.
    """
    salvos = [await _aplicar_item(item) for item in req.plano.itens]
    indexer.rebuild_indices()
    return {"salvos": salvos}


# ---------- API: arquivar (soft, em lugar) ----------

@app.post("/api/docs/{doc_id:path}/archive")
def archive_document(doc_id: str):
    """Arquiva: sai do índice, mas o arquivo permanece no lugar (reversível)."""
    if storage.set_status(doc_id, "arquivado") is None:
        raise HTTPException(404, "Documento não encontrado")
    indexer.rebuild_indices()
    return {"ok": True, "arquivado": doc_id}


@app.post("/api/docs/{doc_id:path}/restore")
def restore_archived(doc_id: str):
    """Restaura um documento arquivado (status volta a 'publicado')."""
    if storage.set_status(doc_id, "publicado") is None:
        raise HTTPException(404, "Documento não encontrado")
    indexer.rebuild_indices()
    return {"ok": True, "restaurado": doc_id}


# ---------- API: lixeira (excluir = mover p/ lixeira; purge só após 30 dias) ----------

@app.post("/api/docs/{doc_id:path}/trash")
def trash_document_route(doc_id: str):
    """Excluir = mover para a lixeira (recuperável; purge só após a retenção)."""
    if storage.trash_document(doc_id) is None:
        raise HTTPException(404, "Documento não encontrado")
    indexer.rebuild_indices()
    return {"ok": True, "lixeira": doc_id}


@app.get("/api/trash")
def list_trash_route():
    """Lista os documentos na lixeira com os dias restantes até poder excluir de vez."""
    itens = []
    for doc in storage.list_trash():
        dias = storage.dias_na_lixeira(doc)
        restante = max(0, config.TRASH_RETENTION_DAYS - dias)
        itens.append({
            "id": doc.id, "titulo": doc.titulo, "assunto": doc.assunto,
            "excluido_em": doc.excluido_em, "dias": dias, "restante": restante,
            "elegivel": restante == 0,
        })
    return {"itens": itens, "retencao_dias": config.TRASH_RETENTION_DAYS}


@app.post("/api/trash/{doc_id:path}/restore")
def restore_trash_route(doc_id: str):
    """Restaura um documento da lixeira de volta ao acervo."""
    if storage.restore_from_trash(doc_id) is None:
        raise HTTPException(404, "Documento não encontrado na lixeira")
    indexer.rebuild_indices()
    return {"ok": True, "restaurado": doc_id}


@app.delete("/api/trash/{doc_id:path}")
def purge_trash_route(doc_id: str):
    """Exclusão definitiva. Só permitida após a retenção (30 dias) na lixeira."""
    resultado = storage.purge_document(doc_id)
    if resultado == "inexistente":
        raise HTTPException(404, "Documento não encontrado na lixeira")
    if resultado == "cedo":
        raise HTTPException(409, f"Só após {config.TRASH_RETENTION_DAYS} dias na lixeira")
    return {"ok": True, "excluido": doc_id}


@app.get("/api/health")
def health():
    return {"ok": True, "model": config.OLLAMA_MODEL, "content": str(config.CONTENT_ROOT)}


# ---------- Front-end React (build de produção do Vite) ----------
# Servido só se `poc/webapp/dist` existir (rode `npm run build` no webapp).
# As rotas /api acima têm precedência; o mount em "/" cobre index.html + assets.

if config.WEB_DIR.exists():
    @app.get("/")
    def root():
        return FileResponse(config.WEB_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(config.WEB_DIR), html=True), name="web")
