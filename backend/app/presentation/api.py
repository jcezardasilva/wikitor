"""Rotas HTTP (FastAPI). Camada fina: delega para os casos de uso em `application`."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..application import (
    assistant_service,
    chat_history_service,
    document_service,
    llm_settings_service,
)
from ..infrastructure import config, settings_repository
from ..infrastructure.llm.base import LLMConfig, LLMError
from .schemas import (
    AssistantRequest,
    CommitRequest,
    LLMModelsRequest,
    LLMSettingsOut,
    LLMSettingsUpdate,
    SaveDocRequest,
)

router = APIRouter()


# ---------- navegação / consulta ----------

@router.get("/api/index")
def get_master_index():
    return document_service.get_master_index()


@router.get("/api/subjects/{assunto}")
def get_subject_index(assunto: str):
    idx = document_service.get_subject_index(assunto)
    if idx is None:
        raise HTTPException(404, "Assunto não encontrado")
    return idx


@router.get("/api/docs/{doc_id:path}")
def get_document(doc_id: str):
    doc = document_service.get_document(doc_id)
    if doc is None:
        raise HTTPException(404, "Documento não encontrado")
    return doc


# ---------- atualização manual ----------

@router.post("/api/docs")
async def save_document(req: SaveDocRequest):
    nivel = req.nivel if req.nivel in config.NIVEIS else "iniciante"
    return await document_service.save_document(
        titulo=req.titulo, assunto=req.assunto, conteudo=req.conteudo,
        nivel=nivel, doc_id=req.id, gerar_resumo=req.gerar_resumo,
    )


# ---------- assistente unificado (responder / autorar / salvar) ----------

@router.post("/api/ai/assistant")
async def ai_assistant(req: AssistantRequest):
    """Turno único do assistente. A IA infere a intenção a partir da conversa.

    Modo árvore (Fase 0): se `arvore`/`plano_pendente`/`proposta_pendente` vierem, usa o
    fluxo ciente da árvore (propõe plano, nunca grava). Senão, mantém o fluxo legado.
    """
    msgs = [m.model_dump() for m in req.messages]
    if req.modo == "arvore" or req.arvore or req.plano_pendente or req.proposta_pendente:
        resultado = await assistant_service.assistente_arvore(
            msgs, req.arvore, req.foco, req.plano_pendente, req.proposta_pendente
        )
    else:
        resultado = await assistant_service.assistente(
            msgs, contexto_doc=req.contexto_doc, doc_id=req.doc_id
        )
    resultado["session_id"] = chat_history_service.registrar_turno(
        req.session_id, msgs, resultado.get("resposta", "")
    )
    return resultado


@router.post("/api/docs/commit")
async def commit_plan(req: CommitRequest):
    """Grava o plano confirmado. Única rota que escreve/remove no modo árvore."""
    salvos = await document_service.commit_plan(req.plano)
    return {"salvos": salvos}


# ---------- arquivar (soft, em lugar) ----------

@router.post("/api/docs/{doc_id:path}/archive")
def archive_document(doc_id: str):
    """Arquiva: sai do índice, mas o arquivo permanece no lugar (reversível)."""
    if document_service.archive_document(doc_id) is None:
        raise HTTPException(404, "Documento não encontrado")
    return {"ok": True, "arquivado": doc_id}


@router.post("/api/docs/{doc_id:path}/restore")
def restore_archived(doc_id: str):
    """Restaura um documento arquivado (status volta a 'publicado')."""
    if document_service.restore_archived(doc_id) is None:
        raise HTTPException(404, "Documento não encontrado")
    return {"ok": True, "restaurado": doc_id}


# ---------- lixeira (excluir = mover p/ lixeira; purge só após 30 dias) ----------

@router.post("/api/docs/{doc_id:path}/trash")
def trash_document_route(doc_id: str):
    """Excluir = mover para a lixeira (recuperável; purge só após a retenção)."""
    if document_service.trash_document(doc_id) is None:
        raise HTTPException(404, "Documento não encontrado")
    return {"ok": True, "lixeira": doc_id}


@router.get("/api/trash")
def list_trash_route():
    return document_service.list_trash()


@router.post("/api/trash/{doc_id:path}/restore")
def restore_trash_route(doc_id: str):
    """Restaura um documento da lixeira de volta ao acervo."""
    if document_service.restore_from_trash(doc_id) is None:
        raise HTTPException(404, "Documento não encontrado na lixeira")
    return {"ok": True, "restaurado": doc_id}


@router.delete("/api/trash/{doc_id:path}")
def purge_trash_route(doc_id: str):
    """Exclusão definitiva. Só permitida após a retenção (30 dias) na lixeira."""
    resultado = document_service.purge_document(doc_id)
    if resultado == "inexistente":
        raise HTTPException(404, "Documento não encontrado na lixeira")
    if resultado == "cedo":
        raise HTTPException(409, f"Só após {config.TRASH_RETENTION_DAYS} dias na lixeira")
    return {"ok": True, "excluido": doc_id}


# ---------- configuração de LLM (provedor ativo) ----------

def _to_out(cfg: LLMConfig) -> LLMSettingsOut:
    return LLMSettingsOut(
        provider=cfg.provider,
        base_url=cfg.base_url,
        model=cfg.model,
        api_key_masked=settings_repository.mask_api_key(cfg.api_key),
        timeout=cfg.timeout,
    )


@router.get("/api/llm/settings", response_model=LLMSettingsOut)
def get_llm_settings():
    return _to_out(llm_settings_service.get_settings())


@router.put("/api/llm/settings", response_model=LLMSettingsOut)
def put_llm_settings(req: LLMSettingsUpdate):
    try:
        cfg = llm_settings_service.update_settings(req.model_dump(exclude_none=True))
    except llm_settings_service.InvalidProvider as exc:
        raise HTTPException(400, str(exc)) from exc
    return _to_out(cfg)


@router.post("/api/llm/models")
async def post_llm_models(req: LLMModelsRequest):
    """Lista modelos do provedor usando os valores do formulário (ainda não salvos)."""
    cfg = LLMConfig(
        provider=req.provider, base_url=req.base_url, model="",
        api_key=req.api_key, timeout=req.timeout,
    )
    try:
        modelos = await llm_settings_service.list_models(cfg)
    except llm_settings_service.InvalidProvider as exc:
        raise HTTPException(400, str(exc)) from exc
    except LLMError as exc:  # provedor fora do ar / credencial inválida → erro claro (D5)
        raise HTTPException(502, f"Não foi possível listar modelos: {exc}") from exc
    return {"models": modelos}


@router.get("/api/health")
def health():
    cfg = llm_settings_service.get_settings()
    return {"ok": True, "provider": cfg.provider, "model": cfg.model,
            "content": str(config.CONTENT_ROOT)}
