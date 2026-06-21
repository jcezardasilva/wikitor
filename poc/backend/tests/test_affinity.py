"""Guarda de afinidade índice↔arquivo (núcleo da correção do bug de sobrescrita)."""
import pytest

from app import config, storage


@pytest.fixture
def docs(tmp_path, monkeypatch):
    d = tmp_path / "docs"
    d.mkdir()
    monkeypatch.setattr(config, "DOCS_DIR", d)
    return d


def _write(docs, doc_id, body="x"):
    p = docs / f"{doc_id}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")


def test_atualiza_quando_assunto_bate(docs):
    _write(docs, "redes/osi")
    assert storage.affinity_target("redes", "redes/osi", "Modelo OSI") == (
        "redes/osi", "atualiza", False,
    )


def test_redireciona_quando_assunto_diverge(docs):
    _write(docs, "redes/osi")
    final_id, tipo, redirecionado = storage.affinity_target("seguranca", "redes/osi", "Firewalls")
    assert tipo == "novo"
    assert redirecionado is True
    assert final_id.startswith("seguranca/")
    assert final_id != "redes/osi"


def test_novo_sem_doc_id_nao_e_redirecionamento(docs):
    final_id, tipo, redirecionado = storage.affinity_target("redes", None, "Sub-redes")
    assert (final_id, tipo, redirecionado) == ("redes/sub-redes", "novo", False)


def test_doc_id_inexistente_vira_novo_no_mesmo_assunto(docs):
    final_id, tipo, redirecionado = storage.affinity_target("redes", "redes/osi", "Modelo OSI")
    assert (final_id, tipo, redirecionado) == ("redes/modelo-osi", "novo", False)
