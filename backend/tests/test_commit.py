"""Endpoint /api/docs/commit — grava o plano com a guarda de afinidade."""
import pytest
from fastapi.testclient import TestClient

from app.application import index_service
from app.infrastructure import config


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DOCS_DIR", tmp_path / "docs")
    monkeypatch.setattr(config, "INDICES_DIR", tmp_path / "indices")

    async def fake_resumo(titulo, conteudo):  # evita chamar Ollama nos testes
        return "resumo de teste"

    monkeypatch.setattr(index_service, "gerar_resumo", fake_resumo)

    from app.main import app
    with TestClient(app) as c:
        yield c


def _doc(tmp_path, doc_id):
    return tmp_path / "docs" / f"{doc_id}.md"


def test_regressao_bug_nao_sobrescreve_arquivo_de_outro_assunto(client, tmp_path):
    antigo = _doc(tmp_path, "redes/osi")
    antigo.parent.mkdir(parents=True, exist_ok=True)
    antigo.write_text("conteudo antigo", encoding="utf-8")

    plano = {"itens": [{
        "node_id": "n1", "assunto": "seguranca", "doc_id": "redes/osi",
        "titulo": "Firewalls", "tipo": "atualiza", "conteudo": "# Firewalls\n\nnovo",
    }]}
    r = client.post("/api/docs/commit", json={"plano": plano})

    assert r.status_code == 200
    salvo = r.json()["salvos"][0]
    assert salvo["assunto"] == "seguranca"
    assert salvo["id"].startswith("seguranca/")
    # o arquivo antigo (assunto redes) permanece intacto
    assert antigo.read_text(encoding="utf-8") == "conteudo antigo"
    # um arquivo novo foi criado sob seguranca
    assert _doc(tmp_path, salvo["id"]).exists()


def test_atualiza_mesmo_arquivo_quando_assunto_bate(client, tmp_path):
    antigo = _doc(tmp_path, "redes/osi")
    antigo.parent.mkdir(parents=True, exist_ok=True)
    antigo.write_text("velho", encoding="utf-8")

    plano = {"itens": [{
        "node_id": "n1", "assunto": "redes", "doc_id": "redes/osi",
        "titulo": "Modelo OSI", "tipo": "atualiza", "conteudo": "# OSI\n\natualizado",
    }]}
    r = client.post("/api/docs/commit", json={"plano": plano})

    assert r.status_code == 200
    assert r.json()["salvos"][0]["id"] == "redes/osi"
    assert "atualizado" in antigo.read_text(encoding="utf-8")
