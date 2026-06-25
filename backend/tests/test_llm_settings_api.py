"""Rotas /api/llm/* — máscara da chave, validação e listagem de modelos."""
import pytest
from fastapi.testclient import TestClient

from app.application import llm_settings_service
from app.infrastructure import config, settings_repository


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "SETTINGS_DIR", tmp_path / "settings")
    from app.main import app
    with TestClient(app) as c:
        yield c


def test_get_default_ollama(client):
    r = client.get("/api/llm/settings")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "ollama"
    assert body["api_key_masked"] is None


def test_put_salva_e_mascarado(client):
    r = client.put("/api/llm/settings", json={
        "provider": "openai_compatible",
        "base_url": "https://api.groq.com/openai",
        "model": "llama-3.1-70b",
        "api_key": "gsk_secret_1234",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "openai_compatible"
    assert body["api_key_masked"] == "…1234"   # nunca a chave real
    assert "api_key" not in body
    # persistido em disco com a chave real
    assert settings_repository.load_llm_config().api_key == "gsk_secret_1234"


def test_put_key_vazia_mantem_atual(client):
    client.put("/api/llm/settings", json={
        "provider": "openai_compatible", "base_url": "https://x",
        "model": "m", "api_key": "gsk_secret_1234",
    })
    r = client.put("/api/llm/settings", json={
        "provider": "openai_compatible", "base_url": "https://x", "model": "outro",
    })
    assert r.status_code == 200
    assert settings_repository.load_llm_config().api_key == "gsk_secret_1234"
    assert r.json()["model"] == "outro"


def test_put_provider_invalido_400(client):
    r = client.put("/api/llm/settings", json={
        "provider": "foobar", "base_url": "https://x", "model": "m",
    })
    assert r.status_code == 400


def test_post_models(client, monkeypatch):
    async def fake_list(cfg):
        return ["a", "b"]

    monkeypatch.setattr(llm_settings_service, "list_models", fake_list)
    r = client.post("/api/llm/models", json={
        "provider": "openai_compatible", "base_url": "https://x", "api_key": "k",
    })
    assert r.status_code == 200
    assert r.json()["models"] == ["a", "b"]


def test_post_models_provedor_fora_do_ar_502(client, monkeypatch):
    from app.infrastructure.llm.base import LLMError

    async def boom(cfg):
        raise LLMError("conexão recusada")

    monkeypatch.setattr(llm_settings_service, "list_models", boom)
    r = client.post("/api/llm/models", json={
        "provider": "openai_compatible", "base_url": "https://x",
    })
    assert r.status_code == 502
