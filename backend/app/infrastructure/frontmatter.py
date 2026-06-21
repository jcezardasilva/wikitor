"""Parse/serialize de frontmatter YAML em arquivos markdown."""
from __future__ import annotations

import datetime as _dt

import yaml

_DELIM = "---"


def _stringify_dates(meta: dict) -> dict:
    """YAML interpreta 'YYYY-MM-DD' como date; mantemos tudo como string."""
    for k, v in meta.items():
        if isinstance(v, (_dt.date, _dt.datetime)):
            meta[k] = v.isoformat()
    return meta


def parse(text: str) -> tuple[dict, str]:
    """Retorna (metadados, corpo). Sem frontmatter → ({}, texto)."""
    if not text.startswith(_DELIM):
        return {}, text
    parts = text.split(_DELIM, 2)
    # parts == ['', '\n<yaml>\n', '\n<corpo>']
    if len(parts) < 3:
        return {}, text
    meta = _stringify_dates(yaml.safe_load(parts[1]) or {})
    body = parts[2].lstrip("\n")
    return meta, body


def dump(meta: dict, body: str) -> str:
    front = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
    return f"{_DELIM}\n{front}\n{_DELIM}\n\n{body.strip()}\n"
