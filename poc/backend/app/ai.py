"""Consumo via IA: geração assistida de conteúdo e Q&A por navegação na cadeia de índices.

O Q&A NÃO usa busca vetorial — segue o design: o LLM lê os índices (resumos + paths),
escolhe os documentos relevantes e responde com base no markdown completo, citando as fontes.
"""
from __future__ import annotations

from . import config, frontmatter, indexer, llm, storage
from .models import Document

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
        messages = [{"role": "user", "content": "Quero criar/editar um documento. Comece a entrevista."}]
    return await llm.chat(messages, system=_coautoria_system(contexto_doc))


async def coautoria_finalizar(messages: list[dict], contexto_doc: str | None = None) -> dict:
    """Sintetiza o documento final em markdown a partir de toda a conversa."""
    instrucao = (
        "Com base em TODA a conversa acima, escreva agora o documento final em markdown. "
        "Comece com um título na primeira linha ('# Título'). Use seções, listas e exemplos "
        "quando fizer sentido. Não inclua comentários fora do documento. Responda apenas com o markdown."
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


_PICK_SYSTEM = (
    "Você seleciona documentos relevantes para responder uma pergunta. "
    "Receberá um índice (lista de documentos com id, titulo, resumo e nivel). "
    "Responda em JSON: {\"ids\": [...]} com os ids dos documentos mais relevantes (no máx. 4). "
    "Se nenhum for relevante, retorne lista vazia."
)

_ANSWER_SYSTEM = (
    "Você responde perguntas usando APENAS o conteúdo fornecido dos documentos da wiki, "
    "em português do Brasil. Cite as fontes pelo título. "
    "Se o conteúdo não cobrir a pergunta, diga claramente que não há informação na wiki."
)


def _flatten_index() -> list[dict]:
    """Lê _master.json → {assunto}.json e devolve entradas achatadas (sem abrir os docs)."""
    master = storage.read_index("_master") or {"assuntos": []}
    entradas: list[dict] = []
    for a in master.get("assuntos", []):
        subj = storage.read_index(a["assunto"])
        if not subj:
            continue
        for nivel, items in subj.get("niveis", {}).items():
            for it in items:
                entradas.append(
                    {"id": it["id"], "titulo": it["titulo"],
                     "resumo": it["resumo"], "nivel": nivel, "assunto": a["assunto"]}
                )
    return entradas


async def perguntar(pergunta: str) -> dict:
    entradas = _flatten_index()
    if not entradas:
        return {"resposta": "A wiki ainda não tem conteúdo indexado.", "fontes": []}

    # Etapa 1 — navegar o índice: LLM escolhe documentos relevantes.
    catalogo = "\n".join(
        f"- id={e['id']} | [{e['nivel']}] {e['titulo']}: {e['resumo']}" for e in entradas
    )
    pick = await llm.generate_json(
        f"Índice da wiki:\n{catalogo}\n\nPergunta: {pergunta}",
        system=_PICK_SYSTEM,
    )
    ids = [i for i in pick.get("ids", []) if any(e["id"] == i for e in entradas)][:4]

    # Etapa 2 — carregar markdown completo dos escolhidos.
    fontes = []
    contexto_blocos = []
    for doc_id in ids:
        doc = storage.read_document(doc_id)
        if doc:
            fontes.append({"id": doc.id, "titulo": doc.titulo})
            contexto_blocos.append(f"## {doc.titulo}\n{doc.conteudo}")

    if not contexto_blocos:
        return {"resposta": "Não encontrei documentos relevantes na wiki para essa pergunta.",
                "fontes": []}

    # Etapa 3 — responder com base no conteúdo.
    contexto = "\n\n---\n\n".join(contexto_blocos)
    resposta = await llm.generate(
        f"Documentos:\n{contexto}\n\nPergunta: {pergunta}\n\nResposta:",
        system=_ANSWER_SYSTEM,
    )
    return {"resposta": resposta, "fontes": fontes}


# ---------- Assistente unificado (responder / autorar / salvar) ----------

_INTENT_SYSTEM = (
    "Você roteia mensagens em um assistente de wiki. Classifique a INTENÇÃO da última "
    "mensagem do usuário, considerando a conversa. Opções:\n"
    "- perguntar: o usuário quer obter informação/tirar dúvida com base no conteúdo da wiki.\n"
    "- autorar: o usuário quer criar ou editar um documento, ou está respondendo às perguntas "
    "do assistente para construir o documento.\n"
    "- salvar: o usuário confirma/pede que o documento seja gerado, salvo ou publicado agora.\n"
    'Responda APENAS JSON: {"intencao": "perguntar|autorar|salvar"}.'
)

_META_SYSTEM = (
    "Dado um documento, classifique-o. Responda APENAS JSON: "
    '{"assunto": "<slug curto, 1-2 palavras>", "nivel": "iniciante|intermediario|avancado"}.'
)


async def _classificar_intencao(messages: list[dict]) -> str:
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-6:])
    try:
        data = await llm.generate_json(
            f"Conversa:\n{convo}\n\nClassifique a última mensagem do usuário.",
            system=_INTENT_SYSTEM,
        )
        intent = str(data.get("intencao", "")).strip().lower()
        if intent in {"perguntar", "autorar", "salvar"}:
            return intent
    except llm.LLMError:
        pass
    return "autorar"  # falha segura: nunca salva por engano; no máximo faz uma pergunta


async def _inferir_meta(titulo: str, conteudo: str) -> tuple[str, str]:
    try:
        data = await llm.generate_json(
            f"Título: {titulo}\nConteúdo:\n{conteudo[:1500]}", system=_META_SYSTEM
        )
        assunto = storage.slugify(str(data.get("assunto") or "geral"))
        nivel = data.get("nivel") if data.get("nivel") in config.NIVEIS else "iniciante"
        return assunto, nivel
    except llm.LLMError:
        return "geral", "iniciante"


async def _finalizar_e_salvar(messages, contexto_doc, doc_id) -> dict:
    draft = await coautoria_finalizar(messages, contexto_doc=contexto_doc)
    titulo, conteudo = draft["titulo"], draft["conteudo"]

    existing = storage.read_document(doc_id) if doc_id else None
    if existing:
        assunto, nivel, the_id = existing.assunto, existing.nivel, existing.id
    else:
        assunto, nivel = await _inferir_meta(titulo, conteudo)
        the_id = storage.new_doc_id(assunto, titulo)

    resumo = await indexer.gerar_resumo(titulo, conteudo)
    doc = Document(
        id=the_id, titulo=titulo, assunto=assunto, nivel=nivel,
        resumo=resumo, conteudo=conteudo, status="publicado",
    )
    storage.write_document(doc)
    indexer.rebuild_indices()
    verbo = "atualizado" if existing else "salvo"
    return {
        "acao": "salvo",
        "resposta": f"✅ Documento {verbo}: **{titulo}** (assunto: {assunto}, nível: {nivel}).",
        "doc": {"id": doc.id, "titulo": titulo},
    }


async def assistente(messages: list[dict], contexto_doc: str | None = None,
                     doc_id: str | None = None) -> dict:
    """Turno único do assistente. A IA decide entre responder, autorar ou salvar."""
    intent = await _classificar_intencao(messages)

    if intent == "salvar":
        return await _finalizar_e_salvar(messages, contexto_doc, doc_id)

    if intent == "perguntar":
        pergunta = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        res = await perguntar(pergunta)
        return {"acao": "resposta", "resposta": res["resposta"], "fontes": res["fontes"]}

    resposta = await coautoria_chat(messages, contexto_doc=contexto_doc)
    return {"acao": "autoria", "resposta": resposta}
