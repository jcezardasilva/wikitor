"""DTOs de request/response da API. Modelos específicos do transporte HTTP."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ..domain.entities import EditNodeIn, NovoDocSugestao, SavePlan


class SaveDocRequest(BaseModel):
    titulo: str
    assunto: str
    conteudo: str
    nivel: str | None = None      # se ausente, IA sugere
    id: str | None = None         # se presente, atualiza; senão cria
    gerar_resumo: bool = True        # usa LLM p/ gerar resumo no save


class AIGenerateRequest(BaseModel):
    tema: str
    assunto: str | None = None
    nivel: str = "iniciante"
    instrucoes: str | None = None


class AIAskRequest(BaseModel):
    pergunta: str


class ChatMessage(BaseModel):
    role: str            # user | assistant
    content: str


class AuthorChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    contexto_doc: str | None = None   # markdown atual, se for edição


class AssistantRequest(BaseModel):
    messages: list[ChatMessage] = Field(default_factory=list)
    contexto_doc: str | None = None   # markdown atual, se editando um doc existente (legado)
    doc_id: str | None = None         # id do doc em edição (legado, single-doc)
    # --- modo árvore (Fase 0) ---
    modo: str | None = None           # "arvore" liga o fluxo ciente da árvore
    arvore: list[EditNodeIn] = Field(default_factory=list)
    foco: str | None = None           # node_id em foco
    plano_pendente: SavePlan | None = None
    proposta_pendente: NovoDocSugestao | None = None
    # --- histórico de interações ---
    session_id: str | None = None     # mantido pelo cliente entre turnos; backend gera se ausente


class CommitRequest(BaseModel):
    plano: SavePlan
