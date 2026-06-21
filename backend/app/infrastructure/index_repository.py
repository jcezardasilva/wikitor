"""Persistência dos índices derivados (JSON), em content/indices/."""
from __future__ import annotations

import json

from . import config


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
