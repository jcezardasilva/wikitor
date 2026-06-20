"""Wikitor — POC. Backend FastAPI: markdown local + Ollama, sem auth/Azure."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import ai, config, indexer, storage
from .models import (
    AssistantRequest,
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
    """Turno único do assistente. A IA infere a intenção a partir da conversa:
    responder dúvidas (Q&A com fontes), conduzir a autoria (entrevista) ou salvar o documento."""
    msgs = [m.model_dump() for m in req.messages]
    return await ai.assistente(msgs, contexto_doc=req.contexto_doc, doc_id=req.doc_id)


@app.get("/api/health")
def health():
    return {"ok": True, "model": config.OLLAMA_MODEL, "content": str(config.CONTENT_ROOT)}


# ---------- Front-end estático ----------

if config.WEB_DIR.exists():
    @app.get("/")
    def root():
        return FileResponse(config.WEB_DIR / "index.html")

    app.mount("/", StaticFiles(directory=str(config.WEB_DIR)), name="web")
