"""Geração e coautoria assistida de conteúdo (entrevista guiada por SKILL.md)."""
from __future__ import annotations

from ..infrastructure import config, frontmatter, llm

_GEN_SYSTEM = (
    "Você é um redator técnico que escreve artigos de wiki em português do Brasil, "
    "em markdown bem estruturado (títulos, listas, exemplos). Não invente fatos."
)


async def gerar_rascunho(tema: str, nivel: str, instrucoes: str | None) -> dict:
    """Gera um rascunho markdown (título + corpo) para revisão humana antes de salvar.

    Geramos markdown puro (mais robusto que JSON em modelos pequenos) e extraímos o
    título do primeiro cabeçalho `#`.
    """
    extra = f"\nInstruções adicionais: {instrucoes}" if instrucoes else ""
    prompt = (
        f"Escreva um documento de wiki sobre: {tema}\n"
        f"Nível do leitor: {nivel} (iniciante/intermediario/avancado).{extra}\n\n"
        "Comece com um título em markdown (linha iniciando com '# '). "
        "Use seções, listas e exemplos. Responda apenas com o markdown."
    )
    conteudo = (await llm.generate(prompt, system=_GEN_SYSTEM)).strip()
    if conteudo.startswith("```"):
        conteudo = conteudo.strip("`").lstrip("markdown").lstrip("\n")

    titulo = tema
    for linha in conteudo.splitlines():
        if linha.startswith("# "):
            titulo = linha[2:].strip()
            break
    return {"titulo": titulo, "conteudo": conteudo, "nivel": nivel}


def _load_skill(name: str) -> str:
    """Lê um SKILL.md e devolve o corpo (sem frontmatter) para usar como system prompt."""
    path = config.SKILLS_DIR / f"{name}.md"
    _, body = frontmatter.parse(path.read_text(encoding="utf-8"))
    return body


def _coautoria_system(contexto_doc: str | None) -> str:
    system = _load_skill("content-authoring")
    if contexto_doc:
        system += f"\n\n## Documento atual (em edição)\n\n{contexto_doc}"
    return system


async def coautoria_chat(messages: list[dict], contexto_doc: str | None = None) -> str:
    """Um turno da entrevista guiada pelo SKILL.md. O cliente mantém o histórico."""
    if not messages:
        # primeira interação: deixa o modelo iniciar a entrevista
        inicio = "Quero criar/editar um documento. Comece a entrevista."
        messages = [{"role": "user", "content": inicio}]
    return await llm.chat(messages, system=_coautoria_system(contexto_doc))


async def coautoria_finalizar(messages: list[dict], contexto_doc: str | None = None) -> dict:
    """Sintetiza o documento final em markdown a partir de toda a conversa."""
    instrucao = (
        "Com base em TODA a conversa acima, escreva agora o documento final em markdown. "
        "Comece com um título na primeira linha ('# Título'). Use seções, listas e exemplos "
        "quando fizer sentido. Não inclua comentários fora do documento. "
        "Responda apenas com o markdown."
    )
    msgs = list(messages) + [{"role": "user", "content": instrucao}]
    conteudo = (await llm.chat(msgs, system=_coautoria_system(contexto_doc))).strip()
    if conteudo.startswith("```"):
        conteudo = conteudo.strip("`").lstrip("markdown").lstrip("\n")
    titulo = ""
    for linha in conteudo.splitlines():
        if linha.startswith("# "):
            titulo = linha[2:].strip()
            break
    return {"titulo": titulo or "Novo documento", "conteudo": conteudo}
