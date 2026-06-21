"""Armazenamento local de markdown. Substitui o Azure Storage na POC.

Layout:
    content/
      docs/{assunto}/{slug}.md       # frontmatter + corpo (fonte da verdade)
      indices/_master.json           # índice raiz (derivado)
      indices/{assunto}.json         # índice por assunto (derivado)
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path

from . import config, frontmatter
from .models import Document, DocumentMeta


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text) or "doc"


def _doc_path(doc_id: str) -> Path:
    return config.DOCS_DIR / f"{doc_id}.md"


def _trash_path(doc_id: str) -> Path:
    return config.TRASH_DIR / f"{doc_id}.md"


def _dump(path: Path, doc: Document) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = DocumentMeta(**doc.model_dump(exclude={"conteudo"})).model_dump()
    path.write_text(frontmatter.dump(meta, doc.conteudo), encoding="utf-8")


def _read(path: Path, doc_id: str) -> Document | None:
    if not path.exists():
        return None
    meta, body = frontmatter.parse(path.read_text(encoding="utf-8"))
    meta.setdefault("id", doc_id)
    meta.setdefault("titulo", path.stem)
    meta.setdefault("assunto", doc_id.split("/", 1)[0] if "/" in doc_id else "geral")
    return Document(**meta, conteudo=body)


def list_documents() -> list[Document]:
    docs: list[Document] = []
    if not config.DOCS_DIR.exists():
        return docs
    for path in sorted(config.DOCS_DIR.rglob("*.md")):
        rel = path.relative_to(config.DOCS_DIR).with_suffix("")
        doc_id = rel.as_posix()
        meta, body = frontmatter.parse(path.read_text(encoding="utf-8"))
        meta.setdefault("id", doc_id)
        meta.setdefault("titulo", path.stem)
        meta.setdefault("assunto", rel.parts[0] if len(rel.parts) > 1 else "geral")
        docs.append(Document(**meta, conteudo=body))
    return docs


def read_document(doc_id: str) -> Document | None:
    path = _doc_path(doc_id)
    if not path.exists():
        return None
    meta, body = frontmatter.parse(path.read_text(encoding="utf-8"))
    meta.setdefault("id", doc_id)
    return Document(**meta, conteudo=body)


def write_document(doc: Document) -> Document:
    _dump(_doc_path(doc.id), doc)
    return doc


def set_status(doc_id: str, status: str) -> Document | None:
    """Altera o status (ex.: 'arquivado' tira do índice; 'publicado' restaura)."""
    doc = read_document(doc_id)
    if doc is None:
        return None
    doc.status = status
    write_document(doc)
    return doc


# ---- Lixeira (soft delete com retenção) ----

def trash_document(doc_id: str) -> Document | None:
    """Move o documento para a lixeira (recuperável). Não apaga de fato."""
    doc = read_document(doc_id)
    if doc is None:
        return None
    doc.status = "lixeira"
    doc.excluido_em = date.today().isoformat()
    _dump(_trash_path(doc_id), doc)
    _doc_path(doc_id).unlink(missing_ok=True)
    return doc


def read_trash(doc_id: str) -> Document | None:
    return _read(_trash_path(doc_id), doc_id)


def list_trash() -> list[Document]:
    docs: list[Document] = []
    if not config.TRASH_DIR.exists():
        return docs
    for path in sorted(config.TRASH_DIR.rglob("*.md")):
        doc_id = path.relative_to(config.TRASH_DIR).with_suffix("").as_posix()
        doc = _read(path, doc_id)
        if doc:
            docs.append(doc)
    return docs


def restore_from_trash(doc_id: str) -> Document | None:
    """Restaura um documento da lixeira de volta ao acervo publicado."""
    doc = read_trash(doc_id)
    if doc is None:
        return None
    doc.status = "publicado"
    doc.excluido_em = None
    _dump(_doc_path(doc_id), doc)
    _trash_path(doc_id).unlink(missing_ok=True)
    return doc


def dias_na_lixeira(doc: Document) -> int:
    if not doc.excluido_em:
        return 0
    return (date.today() - date.fromisoformat(doc.excluido_em)).days


def purge_document(doc_id: str) -> str:
    """Exclusão definitiva a partir da lixeira. Só após a retenção (30 dias).

    Retorna: 'ok' (apagado), 'inexistente', ou 'cedo' (ainda dentro da retenção).
    """
    doc = read_trash(doc_id)
    if doc is None:
        return "inexistente"
    if dias_na_lixeira(doc) < config.TRASH_RETENTION_DAYS:
        return "cedo"
    _trash_path(doc_id).unlink(missing_ok=True)
    return "ok"


def new_doc_id(assunto: str, titulo: str) -> str:
    base = f"{slugify(assunto)}/{slugify(titulo)}"
    doc_id = base
    n = 2
    while _doc_path(doc_id).exists():
        doc_id = f"{base}-{n}"
        n += 1
    return doc_id


def affinity_target(assunto: str, doc_id: str | None, titulo: str) -> tuple[str, str, bool]:
    """Resolve o destino de gravação respeitando a afinidade índice↔arquivo.

    Retorna (doc_id_final, tipo, redirecionado). Esta é a guarda contra o bug de
    sobrescrita: NUNCA devolve um id cujo prefixo de assunto seja diferente de
    `assunto`. Só atualiza um arquivo existente quando o assunto bate com o prefixo
    do `doc_id`; caso contrário cria um arquivo novo sob o assunto correto.
    """
    assunto = slugify(assunto)
    prefixo = doc_id.split("/", 1)[0] if doc_id else None
    if doc_id and prefixo == assunto and _doc_path(doc_id).exists():
        return doc_id, "atualiza", False
    redirecionado = bool(doc_id) and prefixo != assunto
    return new_doc_id(assunto, titulo), "novo", redirecionado


# ---- Índices (derivados) ----

def write_index(name: str, data: dict) -> None:
    config.INDICES_DIR.mkdir(parents=True, exist_ok=True)
    (config.INDICES_DIR / f"{name}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def read_index(name: str) -> dict | None:
    path = config.INDICES_DIR / f"{name}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
