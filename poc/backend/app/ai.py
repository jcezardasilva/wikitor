"""Consumo via IA: geração assistida de conteúdo e Q&A por navegação na cadeia de índices.

O Q&A NÃO usa busca vetorial — segue o design: o LLM lê os índices (resumos + paths),
escolhe os documentos relevantes e responde com base no markdown completo, citando as fontes.
"""
from __future__ import annotations

from . import config, frontmatter, indexer, llm, storage
from .models import Document, EditNodeIn, SavePlan, SavePlanItem

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


# ---------- Assistente ciente da árvore de edição (Fase 0) ----------

_TARGET_SYSTEM = (
    "Você escolhe a qual documento em edição a última mensagem do usuário se aplica. "
    "Receberá a lista de documentos (node_id, assunto, titulo). "
    'Responda APENAS JSON: {"node_id": "<id>"} com o mais provável, ou {"node_id": null}.'
)

_NEWDOC_SYSTEM = (
    "Dado o documento em foco e a última mensagem do usuário, decida se o pedido é sobre ESTE "
    "documento ou introduz um documento/assunto NOVO. Responda APENAS JSON: "
    '{"novo": true|false, "assunto": "<slug 1-2 palavras>", "titulo": "<titulo>", '
    '"nivel": "iniciante|intermediario|avancado"}.'
)

_CONFIRM_SYSTEM = (
    "O usuário recebeu um plano de gravação e respondeu. Classifique a resposta. "
    'Responda APENAS JSON: {"decisao": "confirmar|ajustar|cancelar"}. '
    "confirmar = aceitou gravar; cancelar = não quer gravar; ajustar = quer mudar o plano."
)


def _no(arvore: list[EditNodeIn], node_id: str | None) -> EditNodeIn | None:
    return next((n for n in arvore if n.node_id == node_id), None)


def _para_plano(arvore: list[EditNodeIn]) -> list[EditNodeIn]:
    """Só os nós que mudaram: alterados, ou novos (sem doc_id) com conteúdo."""
    return [n for n in arvore if n.alterado or (n.doc_id is None and n.conteudo.strip())]


async def _rotear_alvo(
    messages: list[dict], arvore: list[EditNodeIn], foco: str | None
) -> str | None:
    if not arvore:
        return None
    if len(arvore) == 1:
        return arvore[0].node_id
    catalogo = "\n".join(f"- node_id={n.node_id} | [{n.assunto}] {n.titulo}" for n in arvore)
    ultimo = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    try:
        data = await llm.generate_json(
            f"Documentos:\n{catalogo}\n\nMensagem: {ultimo}", system=_TARGET_SYSTEM
        )
        nid = data.get("node_id")
        if any(n.node_id == nid for n in arvore):
            return nid
    except llm.LLMError:
        pass
    return foco or arvore[0].node_id


async def _detectar_novo_doc(messages: list[dict], no_foco: EditNodeIn | None) -> dict | None:
    if no_foco is None:
        return None
    ultimo = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    try:
        data = await llm.generate_json(
            f"Documento em foco: assunto={no_foco.assunto}, titulo={no_foco.titulo}\n"
            f"Mensagem do usuário: {ultimo}",
            system=_NEWDOC_SYSTEM,
        )
        if not data.get("novo"):
            return None
        nivel = data.get("nivel") if data.get("nivel") in config.NIVEIS else "iniciante"
        return {
            "assunto": storage.slugify(str(data.get("assunto") or no_foco.assunto)),
            "titulo": str(data.get("titulo") or "Novo documento"),
            "nivel": nivel,
        }
    except llm.LLMError:
        return None


async def _ultimo_user(messages: list[dict]) -> str:
    return next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")


_REMOCAO_SYSTEM = (
    "Classifique se a última mensagem do usuário pede para REMOVER ou ARQUIVAR um documento. "
    'Responda APENAS JSON: {"acao": "remover|arquivar|nenhum"}. '
    "remover = excluir definitivamente; arquivar = tornar obsoleto/tirar de circulação; "
    "nenhum = não é pedido de remoção."
)


async def _detectar_remocao(messages: list[dict], no_foco: EditNodeIn | None) -> str | None:
    if no_foco is None or not no_foco.doc_id:
        return None
    ultimo = await _ultimo_user(messages)
    try:
        data = await llm.generate_json(ultimo, system=_REMOCAO_SYSTEM)
        acao = str(data.get("acao", "")).strip().lower()
    except llm.LLMError:
        return None
    return acao if acao in {"remover", "arquivar"} else None


def _plano_remocao(no: EditNodeIn, acao: str) -> dict:
    item = SavePlanItem(
        node_id=no.node_id, assunto=no.assunto, doc_id=no.doc_id,
        arquivo=f"docs/{no.doc_id}.md", titulo=no.titulo, nivel=no.nivel,
        tipo=acao, redirecionado=False, conteudo="",
    )
    plano = SavePlan(itens=[item])
    verbo = "remover (excluir)" if acao == "remover" else "arquivar"
    return {
        "acao": "plano_save",
        "resposta": f"Vou {verbo}: docs/{no.doc_id}.md\n\nConfirma?",
        "plano": plano.model_dump(),
    }


async def _detectar_drift(messages: list[dict], no: EditNodeIn | None) -> str | None:
    """Sinaliza deriva de assunto durante a edição, a partir da conversa (decisão B)."""
    if no is None or not no.assunto:
        return None
    ultimo = await _ultimo_user(messages)
    if not ultimo.strip():
        return None
    assunto_inferido, _ = await _inferir_meta(no.titulo or "documento", ultimo)
    return assunto_inferido if assunto_inferido and assunto_inferido != no.assunto else None


async def _autorar_em_novo(messages: list[dict]) -> dict:
    """Árvore vazia / sem foco: não há arquivo a proteger, então cria um nó de trabalho."""
    resposta = await coautoria_chat(messages, contexto_doc=None)
    return {
        "acao": "novo_no_auto",
        "resposta": resposta,
        "sugestao": {"assunto": "", "titulo": "", "nivel": "iniciante"},
    }


async def _item_plano(no: EditNodeIn, messages: list[dict]) -> SavePlanItem:
    # O conteúdo é sintetizado da conversa por nó (como no fluxo legado), com o texto
    # atual do nó como contexto; a afinidade então decide o destino.
    draft = await coautoria_finalizar(messages, contexto_doc=no.conteudo or None)
    conteudo = draft["conteudo"]
    titulo = no.titulo or draft["titulo"]
    assunto_inferido, nivel = await _inferir_meta(titulo, conteudo)
    assunto = assunto_inferido or no.assunto or "geral"
    final_id, tipo, redirecionado = storage.affinity_target(assunto, no.doc_id, titulo)
    return SavePlanItem(
        node_id=no.node_id,
        assunto=assunto,
        doc_id=no.doc_id,
        arquivo=f"docs/{final_id}.md",
        titulo=titulo,
        nivel=no.nivel or nivel,
        tipo=tipo,
        redirecionado=redirecionado,
        conteudo=conteudo,
    )


def _descreve_plano(plano: SavePlan) -> str:
    if not plano.itens:
        return "Não há alterações para gravar."
    linhas = []
    for it in plano.itens:
        marca = " (redirecionado p/ afinidade)" if it.redirecionado else ""
        linhas.append(f"- {it.arquivo} — {it.tipo}{marca}")
    corpo = "\n".join(linhas)
    return f"Vou gravar:\n{corpo}\n\nConfirma?"


async def _propor_plano(arvore: list[EditNodeIn], messages: list[dict]) -> dict:
    itens = [await _item_plano(n, messages) for n in _para_plano(arvore)]
    plano = SavePlan(itens=itens)
    return {"acao": "plano_save", "resposta": _descreve_plano(plano), "plano": plano.model_dump()}


async def _resolver_confirmacao(messages: list[dict], plano: SavePlan,
                                arvore: list[EditNodeIn]) -> dict:
    ultimo = await _ultimo_user(messages)
    try:
        data = await llm.generate_json(ultimo, system=_CONFIRM_SYSTEM)
        decisao = str(data.get("decisao", "")).strip().lower()
    except llm.LLMError:
        decisao = "ajustar"  # falha segura: nunca grava sem confirmar
    if decisao == "confirmar":
        return {"acao": "confirmado", "resposta": "Gravando…", "plano": plano.model_dump()}
    if decisao == "cancelar":
        return {"acao": "cancelado", "resposta": "Ok, não vou gravar."}
    return await _propor_plano(arvore, messages)  # ajustar: remonta da árvore atual


async def _resolver_proposta(messages: list[dict]) -> dict:
    ultimo = await _ultimo_user(messages)
    try:
        data = await llm.generate_json(ultimo, system=_CONFIRM_SYSTEM)
        decisao = str(data.get("decisao", "")).strip().lower()
    except llm.LLMError:
        decisao = "cancelar"
    if decisao == "confirmar":
        return {"acao": "criar_no", "resposta": "Documento adicionado à árvore."}
    return {"acao": "cancelado", "resposta": "Mantendo o documento atual."}


async def assistente_arvore(messages: list[dict], arvore: list[EditNodeIn], foco: str | None,
                            plano_pendente: SavePlan | None,
                            proposta_pendente) -> dict:
    """Turno do assistente ciente da árvore. Propõe — nunca grava (isso é o /docs/commit)."""
    if plano_pendente is not None:
        return await _resolver_confirmacao(messages, plano_pendente, arvore)
    if proposta_pendente is not None:
        return await _resolver_proposta(messages)

    intent = await _classificar_intencao(messages)
    if intent == "perguntar":
        pergunta = await _ultimo_user(messages)
        res = await perguntar(pergunta)
        return {"acao": "resposta", "resposta": res["resposta"], "fontes": res["fontes"]}
    if intent == "salvar":
        return await _propor_plano(arvore, messages)

    no_foco = _no(arvore, foco)
    if no_foco is None:
        return await _autorar_em_novo(messages)  # nada a proteger: cria nó de trabalho

    remocao = await _detectar_remocao(messages, no_foco)
    if remocao:
        return _plano_remocao(no_foco, remocao)

    sugestao = await _detectar_novo_doc(messages, no_foco)
    if sugestao:
        return {
            "acao": "propor_novo_doc",
            "resposta": f"Isso parece um novo documento (assunto: {sugestao['assunto']}). Criar?",
            "sugestao": sugestao,
        }

    alvo = await _rotear_alvo(messages, arvore, foco)
    no_alvo = _no(arvore, alvo) or no_foco
    resposta = await coautoria_chat(messages, contexto_doc=no_alvo.conteudo or None)
    out = {"acao": "autoria", "alvo": no_alvo.node_id, "resposta": resposta}
    drift = await _detectar_drift(messages, no_alvo)
    if drift:
        out["drift"] = {"node_id": no_alvo.node_id, "assunto_sugerido": drift}
    return out
