"""Provedores de LLM: mapeamento de resposta e de erro (httpx mockado)."""
import httpx
import pytest

from app.infrastructure import llm
from app.infrastructure.llm import generate_json
from app.infrastructure.llm.base import LLMConfig, LLMError
from app.infrastructure.llm.ollama import OllamaProvider
from app.infrastructure.llm.openai_compatible import OpenAICompatibleProvider


def _mock_transport(handler):
    return httpx.MockTransport(handler)


@pytest.fixture(autouse=True)
def patch_async_client(monkeypatch):
    """Permite injetar um transport por teste via variável de módulo."""
    holder = {}

    real_init = httpx.AsyncClient.__init__

    def init(self, *args, **kwargs):
        if "transport" in holder:
            kwargs["transport"] = holder["transport"]
        real_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", init)
    return holder


def _cfg(provider):
    return LLMConfig(provider=provider, base_url="http://x", model="m", api_key="k")


@pytest.mark.anyio
async def test_openai_generate(patch_async_client):
    def handler(req: httpx.Request):
        assert req.url.path == "/v1/chat/completions"
        assert req.headers["authorization"] == "Bearer k"
        return httpx.Response(200, json={"choices": [{"message": {"content": " oi "}}]})

    patch_async_client["transport"] = _mock_transport(handler)
    out = await OpenAICompatibleProvider(_cfg("openai_compatible")).generate("p")
    assert out == "oi"


@pytest.mark.anyio
async def test_openai_list_models(patch_async_client):
    def handler(req):
        assert req.url.path == "/v1/models"
        return httpx.Response(200, json={"data": [{"id": "a"}, {"id": "b"}]})

    patch_async_client["transport"] = _mock_transport(handler)
    models = await OpenAICompatibleProvider(_cfg("openai_compatible")).list_models()
    assert models == ["a", "b"]


@pytest.mark.anyio
async def test_openai_http_error_vira_llmerror(patch_async_client):
    def handler(req):
        return httpx.Response(401, json={"error": "bad key"})

    patch_async_client["transport"] = _mock_transport(handler)
    with pytest.raises(LLMError):
        await OpenAICompatibleProvider(_cfg("openai_compatible")).generate("p")


@pytest.mark.anyio
async def test_ollama_generate(patch_async_client):
    def handler(req):
        assert req.url.path == "/api/generate"
        return httpx.Response(200, json={"response": " resposta "})

    patch_async_client["transport"] = _mock_transport(handler)
    out = await OllamaProvider(_cfg("ollama")).generate("p")
    assert out == "resposta"


@pytest.mark.anyio
async def test_ollama_list_models(patch_async_client):
    def handler(req):
        assert req.url.path == "/api/tags"
        return httpx.Response(200, json={"models": [{"name": "llama"}, {"name": "gemma"}]})

    patch_async_client["transport"] = _mock_transport(handler)
    assert await OllamaProvider(_cfg("ollama")).list_models() == ["llama", "gemma"]


def test_build_provider_seleciona_classe():
    assert isinstance(llm.build_provider(_cfg("openai_compatible")), OpenAICompatibleProvider)
    assert isinstance(llm.build_provider(_cfg("ollama")), OllamaProvider)
    # provider desconhecido cai no default Ollama
    assert isinstance(llm.build_provider(_cfg("qualquer")), OllamaProvider)


@pytest.mark.anyio
async def test_generate_json_tolera_cercas(monkeypatch):
    async def fake_generate(prompt, system=None, as_json=False):
        return "```json\n{\"a\": 1}\n```"

    monkeypatch.setattr(llm, "generate", fake_generate)
    assert await generate_json("p") == {"a": 1}
