"""Histórico de interações do assistente: uma sessão por arquivo em content/chats/."""
import pytest
from fastapi.testclient import TestClient

from app.application import assistant_service, chat_history_service, index_service
from app.infrastructure import chat_repository, config


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DOCS_DIR", tmp_path / "docs")
    monkeypatch.setattr(config, "INDICES_DIR", tmp_path / "indices")
    monkeypatch.setattr(config, "CHATS_DIR", tmp_path / "chats")

    async def fake_resumo(titulo, conteudo):
        return "resumo de teste"

    monkeypatch.setattr(index_service, "gerar_resumo", fake_resumo)

    async def fake_assistente_arvore(messages, arvore, foco, plano_pendente, proposta_pendente):
        return {"acao": "autoria", "resposta": "resposta de teste"}

    monkeypatch.setattr(assistant_service, "assistente_arvore", fake_assistente_arvore)

    from app.main import app
    with TestClient(app) as c:
        yield c


def _chat_path(tmp_path, session_id):
    return tmp_path / "chats" / f"{session_id}.md"


def test_registrar_turno_gera_session_id_quando_ausente(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHATS_DIR", tmp_path / "chats")
    sid = chat_history_service.registrar_turno(None, [{"role": "user", "content": "oi"}], "olá")
    assert sid
    assert _chat_path(tmp_path, sid).exists()


def test_registrar_turno_reusa_session_id_informado(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHATS_DIR", tmp_path / "chats")
    sid = chat_history_service.registrar_turno(
        "sessao-1", [{"role": "user", "content": "oi"}], "olá"
    )
    assert sid == "sessao-1"


def test_write_session_preserva_criado_em_entre_turnos(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "CHATS_DIR", tmp_path / "chats")
    chat_repository.write_session("s1", [{"role": "user", "content": "primeiro"}])
    primeiro = chat_repository.read_session_meta("s1")

    chat_repository.write_session(
        "s1",
        [
            {"role": "user", "content": "primeiro"},
            {"role": "assistant", "content": "resp"},
            {"role": "user", "content": "segundo"},
        ],
    )
    segundo = chat_repository.read_session_meta("s1")

    assert segundo["criado_em"] == primeiro["criado_em"]
    assert segundo["total_mensagens"] == 3


def test_endpoint_assistant_grava_sessao_e_retorna_session_id(client, tmp_path):
    payload = {
        "messages": [{"role": "user", "content": "o que é uma sub-rede?"}],
        "modo": "arvore",
    }
    r = client.post("/api/ai/assistant", json=payload)
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"]
    assert _chat_path(tmp_path, body["session_id"]).exists()


def test_endpoint_assistant_reusa_session_id_enviado(client, tmp_path):
    payload = {
        "messages": [{"role": "user", "content": "oi"}],
        "modo": "arvore",
        "session_id": "sessao-fixa",
    }
    r = client.post("/api/ai/assistant", json=payload)
    assert r.json()["session_id"] == "sessao-fixa"
    assert _chat_path(tmp_path, "sessao-fixa").exists()
