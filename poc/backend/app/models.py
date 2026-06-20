"""Modelos da POC (pydantic). Versão simplificada do design: sem tenant/grupos/auth."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class DocumentMeta(BaseModel):
    """Frontmatter do documento — fonte da verdade. Índices são derivados disto."""
    id: str                      # "{assunto}/{slug}"
    titulo: str
    assunto: str
    nivel: str = "iniciante"     # iniciante | intermediario | avancado
    resumo: str = ""             # gerado por LLM
    status: str = "publicado"    # rascunho | publicado
    referencias: list[str] = Field(default_factory=list)
    atualizado_em: str = Field(default_factory=lambda: date.today().isoformat())


class Document(DocumentMeta):
    conteudo: str = ""           # corpo markdown


class IndexEntry(BaseModel):
    id: str
    path: str
    titulo: str
    resumo: str
    nivel: str


class SubjectIndex(BaseModel):
    assunto: str
    resumo: str = ""
    niveis: dict[str, list[IndexEntry]] = Field(default_factory=dict)
    relacionados: list[str] = Field(default_factory=list)


class MasterIndexEntry(BaseModel):
    assunto: str
    resumo: str
    path: str
    total_docs: int


class MasterIndex(BaseModel):
    assuntos: list[MasterIndexEntry] = Field(default_factory=list)


# ---- Payloads de request ----

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
    contexto_doc: str | None = None   # markdown atual, se editando um doc existente
    doc_id: str | None = None         # id do doc em edição (para atualizar o mesmo arquivo)
