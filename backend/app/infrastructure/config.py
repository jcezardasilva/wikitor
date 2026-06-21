"""Configuração da POC. Tudo via variáveis de ambiente, com defaults sensatos."""
import os
from pathlib import Path

# Raiz do repositório: .../wikitor
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Onde os markdown e índices vivem (sem Azure — sistema de arquivos local).
CONTENT_ROOT = Path(os.getenv("Wikitor_CONTENT_ROOT", _REPO_ROOT / "content"))
DOCS_DIR = CONTENT_ROOT / "docs"
INDICES_DIR = CONTENT_ROOT / "indices"
# Lixeira: "excluir" move o .md para cá; só após N dias a exclusão é definitiva.
TRASH_DIR = CONTENT_ROOT / "trash"
TRASH_RETENTION_DAYS = int(os.getenv("Wikitor_TRASH_RETENTION_DAYS", "30"))

# Histórico de sessões do assistente — uma sessão por arquivo (ver chat_repository).
CHATS_DIR = CONTENT_ROOT / "chats"

# Front-end React (Vite) servido pelo próprio FastAPI a partir do build de produção.
# Em dev, use `npm run dev` no webapp (proxy /api -> :8000); em prod, `npm run build`.
WEB_DIR = Path(os.getenv("Wikitor_WEB_DIR", _REPO_ROOT / "webapp" / "dist"))

# Skills (instruções estilo SKILL.md usadas como system prompt do LLM).
SKILLS_DIR = Path(os.getenv("Wikitor_SKILLS_DIR", _REPO_ROOT / "backend" / "skills"))

# Ollama (provedor LLM local).
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
OLLAMA_TIMEOUT = float(os.getenv("OLLAMA_TIMEOUT", "120"))

# Níveis de maturidade válidos (dimensão da cadeia de índices).
NIVEIS = ["iniciante", "intermediario", "avancado"]


def ensure_dirs() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    INDICES_DIR.mkdir(parents=True, exist_ok=True)
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    CHATS_DIR.mkdir(parents=True, exist_ok=True)
