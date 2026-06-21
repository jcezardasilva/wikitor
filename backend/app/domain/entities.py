"""Entidades de domínio: documentos, índices e o plano de edição em árvore.

Sem dependência de infraestrutura (filesystem, HTTP, LLM) — só regras e formas
de dados que valem independentemente de onde/como são persistidas ou expostas.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

from pydantic import BaseModel, Field


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text) or "doc"


class DocumentMeta(BaseModel):
    """Frontmatter do documento — fonte da verdade. Índices são derivados disto."""
    id: str                      # "{assunto}/{slug}"
    titulo: str
    assunto: str
    nivel: str = "iniciante"     # iniciante | intermediario | avancado
    resumo: str = ""             # gerado por LLM
    status: str = "publicado"    # rascunho | publicado | arquivado | lixeira
    referencias: list[str] = Field(default_factory=list)
    atualizado_em: str = Field(default_factory=lambda: date.today().isoformat())
    excluido_em: str | None = None   # data de envio à lixeira (None = não está na lixeira)


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


# ---- Árvore de edição (estado de sessão do cliente) e plano de gravação ----

class EditNodeIn(BaseModel):
    """Nó da árvore de edição (estado de sessão do cliente) enviado a cada turno."""
    node_id: str
    assunto: str
    doc_id: str | None = None         # null = documento novo (sem arquivo)
    titulo: str = ""
    nivel: str = "iniciante"
    conteudo: str = ""
    alterado: bool = False            # cliente marca quando o conteúdo mudou


class NovoDocSugestao(BaseModel):
    assunto: str
    titulo: str
    nivel: str = "iniciante"


class SavePlanItem(BaseModel):
    node_id: str
    assunto: str                      # assunto final (após afinidade)
    doc_id: str | None = None         # id de origem; o commit re-deriva o destino
    arquivo: str = ""                 # caminho previsto (exibição) docs/{assunto}/{slug}.md
    titulo: str
    nivel: str = "iniciante"
    tipo: str = "novo"                # novo | atualiza
    redirecionado: bool = False       # afinidade mudou o destino (A em arquivo de B)
    conteudo: str = ""                # snapshot do texto a gravar


class SavePlan(BaseModel):
    itens: list[SavePlanItem] = Field(default_factory=list)
