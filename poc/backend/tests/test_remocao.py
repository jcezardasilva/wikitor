"""Arquivar (soft, em lugar) e Lixeira (excluir = mover; purge só após 30 dias)."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app import config, indexer, storage
from app.models import Document


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DOCS_DIR", tmp_path / "docs")
    monkeypatch.setattr(config, "INDICES_DIR", tmp_path / "indices")
    monkeypatch.setattr(config, "TRASH_DIR", tmp_path / "trash")

    async def fake_resumo(titulo, conteudo):
        return "resumo de teste"

    monkeypatch.setattr(indexer, "gerar_resumo", fake_resumo)

    from app.main import app
    with TestClient(app) as c:
        yield c


def _seed(doc_id="redes/osi", assunto="redes", titulo="OSI"):
    return storage.write_document(Document(
        id=doc_id, titulo=titulo, assunto=assunto, nivel="iniciante",
        resumo="r", conteudo="# OSI", status="publicado",
    ))


def _antecipar_exclusao(doc_id, dias):
    """Recua a data de exclusão para simular tempo na lixeira."""
    doc = storage.read_trash(doc_id)
    doc.excluido_em = (date.today() - timedelta(days=dias)).isoformat()
    storage._dump(storage._trash_path(doc_id), doc)


# ---- arquivar (em lugar) ----

def test_archive_mantem_arquivo_mas_tira_do_indice(client, tmp_path):
    _seed()
    assert client.post("/api/docs/redes/osi/archive").status_code == 200
    doc = storage.read_document("redes/osi")
    assert doc is not None and doc.status == "arquivado"
    master = storage.read_index("_master") or {"assuntos": []}
    assert all(a["assunto"] != "redes" for a in master["assuntos"])


def test_restore_arquivado(client):
    _seed()
    client.post("/api/docs/redes/osi/archive")
    assert client.post("/api/docs/redes/osi/restore").status_code == 200
    assert storage.read_document("redes/osi").status == "publicado"


# ---- lixeira ----

def test_excluir_move_para_lixeira(client, tmp_path):
    _seed()
    r = client.post("/api/docs/redes/osi/trash")
    assert r.status_code == 200
    # saiu do acervo, foi para a lixeira
    assert not (tmp_path / "docs" / "redes" / "osi.md").exists()
    assert (tmp_path / "trash" / "redes" / "osi.md").exists()
    doc = storage.read_trash("redes/osi")
    assert doc.status == "lixeira" and doc.excluido_em == date.today().isoformat()


def test_excluir_inexistente_404(client):
    assert client.post("/api/docs/nao/existe/trash").status_code == 404


def test_lista_lixeira_mostra_dias_restantes(client):
    _seed()
    client.post("/api/docs/redes/osi/trash")
    r = client.get("/api/trash")
    body = r.json()
    assert body["retencao_dias"] == 30
    item = body["itens"][0]
    assert item["id"] == "redes/osi"
    assert item["restante"] == 30 and item["elegivel"] is False


def test_restaurar_da_lixeira(client, tmp_path):
    _seed()
    client.post("/api/docs/redes/osi/trash")
    r = client.post("/api/trash/redes/osi/restore")
    assert r.status_code == 200
    assert (tmp_path / "docs" / "redes" / "osi.md").exists()
    assert not (tmp_path / "trash" / "redes" / "osi.md").exists()
    assert storage.read_document("redes/osi").status == "publicado"


def test_purge_antes_dos_30_dias_bloqueado(client):
    _seed()
    client.post("/api/docs/redes/osi/trash")
    assert client.delete("/api/trash/redes/osi").status_code == 409


def test_purge_apos_retencao_apaga_definitivo(client, tmp_path):
    _seed()
    client.post("/api/docs/redes/osi/trash")
    _antecipar_exclusao("redes/osi", 31)
    r = client.delete("/api/trash/redes/osi")
    assert r.status_code == 200
    assert not (tmp_path / "trash" / "redes" / "osi.md").exists()


def test_commit_remover_move_para_lixeira(client, tmp_path):
    _seed(doc_id="seguranca/firewalls", assunto="seguranca", titulo="Firewalls")
    plano = {"itens": [{
        "node_id": "n1", "assunto": "seguranca", "doc_id": "seguranca/firewalls",
        "titulo": "Firewalls", "tipo": "remover", "conteudo": "",
    }]}
    r = client.post("/api/docs/commit", json={"plano": plano})
    assert r.status_code == 200
    assert r.json()["salvos"][0]["tipo"] == "lixeira"
    assert not (tmp_path / "docs" / "seguranca" / "firewalls.md").exists()
    assert (tmp_path / "trash" / "seguranca" / "firewalls.md").exists()
