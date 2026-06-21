"""Classificação de intenção da conversa e inferência de metadados do documento.

Compartilhado pelo fluxo legado (`legacy.py`) e pelo modo árvore (`tree_assistant.py`).
"""
from __future__ import annotations

from ...domain.entities import slugify
from ...infrastructure import config, ollama_client

INTENT_SYSTEM = (
    "Você roteia mensagens em um assistente de wiki. Classifique a INTENÇÃO da última "
    "mensagem do usuário, considerando a conversa. Opções:\n"
    "- perguntar: o usuário quer obter informação/tirar dúvida com base no conteúdo da wiki.\n"
    "- autorar: o usuário quer criar ou editar um documento, ou está respondendo às perguntas "
    "do assistente para construir o documento.\n"
    "- salvar: o usuário confirma/pede que o documento seja gerado, salvo ou publicado agora.\n"
    'Responda APENAS JSON: {"intencao": "perguntar|autorar|salvar"}.'
)

META_SYSTEM = (
    "Dado um documento, classifique-o. Responda APENAS JSON: "
    '{"assunto": "<slug curto, 1-2 palavras>", "nivel": "iniciante|intermediario|avancado"}.'
)


async def classificar_intencao(messages: list[dict]) -> str:
    convo = "\n".join(f"{m['role']}: {m['content']}" for m in messages[-6:])
    try:
        data = await ollama_client.generate_json(
            f"Conversa:\n{convo}\n\nClassifique a última mensagem do usuário.",
            system=INTENT_SYSTEM,
        )
        intent = str(data.get("intencao", "")).strip().lower()
        if intent in {"perguntar", "autorar", "salvar"}:
            return intent
    except ollama_client.LLMError:
        pass
    return "autorar"  # falha segura: nunca salva por engano; no máximo faz uma pergunta


async def inferir_meta(titulo: str, conteudo: str) -> tuple[str, str]:
    try:
        data = await ollama_client.generate_json(
            f"Título: {titulo}\nConteúdo:\n{conteudo[:1500]}", system=META_SYSTEM
        )
        assunto = slugify(str(data.get("assunto") or "geral"))
        nivel = data.get("nivel") if data.get("nivel") in config.NIVEIS else "iniciante"
        return assunto, nivel
    except ollama_client.LLMError:
        return "geral", "iniciante"
