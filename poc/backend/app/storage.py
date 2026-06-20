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
from pathlib import Path

from . import config, frontmatter
from .models import Document, DocumentMeta


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[\s_-]+", "-", text) or "doc"


def _doc_path(doc_id: str) -> Path:
    return config.DOCS_DIR / f"{doc_id}.md"


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
    path = _doc_path(doc.id)
    path.parent.mkdir(parents=True, exist_ok=True)
    meta = DocumentMeta(**doc.model_dump(exclude={"conteudo"})).model_dump()
    path.write_text(frontmatter.dump(meta, doc.conteudo), encoding="utf-8")
    return doc


def new_doc_id(assunto: str, titulo: str) -> str:
    base = f"{slugify(assunto)}/{slugify(titulo)}"
    doc_id = base
    n = 2
    while _doc_path(doc_id).exists():
        doc_id = f"{base}-{n}"
        n += 1
    return doc_id


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
