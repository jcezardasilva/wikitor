"""Persistência e segurança das settings de LLM."""
import pytest

from app.infrastructure import config, settings_repository


@pytest.fixture
def settings_dir(tmp_path, monkeypatch):
    d = tmp_path / "settings"
    monkeypatch.setattr(config, "SETTINGS_DIR", d)
    return d


def test_default_quando_nao_ha_arquivo(settings_dir, monkeypatch):
    monkeypatch.setattr(config, "OLLAMA_URL", "http://localhost:11434")
    monkeypatch.setattr(config, "OLLAMA_MODEL", "gemma4:e2b")
    cfg = settings_repository.load_llm_config()
    assert cfg.provider == "ollama"
    assert cfg.base_url == "http://localhost:11434"
    assert cfg.model == "gemma4:e2b"
    assert cfg.api_key is None


def test_save_e_load_roundtrip(settings_dir):
    settings_repository.save_llm_config({
        "provider": "openai_compatible",
        "base_url": "https://api.groq.com/openai",
        "model": "llama-3.1-70b",
        "api_key": "gsk_secret_1234",
    })
    cfg = settings_repository.load_llm_config()
    assert cfg.provider == "openai_compatible"
    assert cfg.base_url == "https://api.groq.com/openai"
    assert cfg.model == "llama-3.1-70b"
    assert cfg.api_key == "gsk_secret_1234"


def test_api_key_vazia_mantem_a_atual(settings_dir):
    settings_repository.save_llm_config({
        "provider": "openai_compatible", "base_url": "https://x", "model": "m",
        "api_key": "gsk_secret_1234",
    })
    # update sem key (ex.: usuário só trocou o modelo)
    settings_repository.save_llm_config({"model": "outro-modelo"})
    cfg = settings_repository.load_llm_config()
    assert cfg.api_key == "gsk_secret_1234"  # preservada
    assert cfg.model == "outro-modelo"


def test_api_key_nova_substitui(settings_dir):
    settings_repository.save_llm_config({
        "provider": "openai_compatible", "base_url": "https://x", "model": "m",
        "api_key": "antiga",
    })
    settings_repository.save_llm_config({"api_key": "nova"})
    assert settings_repository.load_llm_config().api_key == "nova"


def test_escrita_atomica_nao_deixa_tmp(settings_dir):
    settings_repository.save_llm_config(
        {"provider": "ollama", "base_url": "http://x", "model": "m"}
    )
    tmp = settings_dir / "llm.json.tmp"
    assert not tmp.exists()
    assert (settings_dir / "llm.json").exists()


def test_arquivo_corrompido_cai_no_default(settings_dir):
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "llm.json").write_text("{ nao eh json", encoding="utf-8")
    cfg = settings_repository.load_llm_config()
    assert cfg.provider == "ollama"


@pytest.mark.parametrize("key,esperado", [
    (None, None),
    ("", None),
    ("ab", "…ab"),
    ("gsk_secret_1234", "…1234"),
])
def test_mask_api_key(key, esperado):
    assert settings_repository.mask_api_key(key) == esperado
