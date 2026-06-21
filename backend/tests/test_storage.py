from app.domain.entities import slugify


def test_slugify_removes_accents_and_lowercases():
    assert slugify("Configuração de Rede") == "configuracao-de-rede"


def test_slugify_collapses_separators():
    assert slugify("  Olá   Mundo!! ") == "ola-mundo"


def test_slugify_empty_string_falls_back_to_doc():
    assert slugify("") == "doc"
