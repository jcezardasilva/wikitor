"""Roteamento de alvo e detecção de intenções estruturais dentro da árvore de edição.

Dado o estado da árvore (nós em edição) e a última mensagem do usuário, decide a qual
nó ela se aplica e se sinaliza remoção, novo documento ou deriva de assunto.
"""
from __future__ import annotations

from ...domain.entities import EditNodeIn, slugify
from ...infrastructure import config, ollama_client
from . import intent

TARGET_SYSTEM = (
    "Você escolhe a qual documento em edição a última mensagem do usuário se aplica. "
    "Receberá a lista de documentos (node_id, assunto, titulo). "
    'Responda APENAS JSON: {"node_id": "<id>"} com o mais provável, ou {"node_id": null}.'
)

NEWDOC_SYSTEM = (
    "Dado o documento em foco e a última mensagem do usuário, decida se o pedido é sobre ESTE "
    "documento ou introduz um documento/assunto NOVO. Responda APENAS JSON: "
    '{"novo": true|false, "assunto": "<slug 1-2 palavras>", "titulo": "<titulo>", '
    '"nivel": "iniciante|intermediario|avancado"}.'
)

REMOCAO_SYSTEM = (
    "Classifique se a última mensagem do usuário pede para REMOVER ou ARQUIVAR um documento. "
    'Responda APENAS JSON: {"acao": "remover|arquivar|nenhum"}. '
    "remover = excluir definitivamente; arquivar = tornar obsoleto/tirar de circulação; "
    "nenhum = não é pedido de remoção."
)


def no(arvore: list[EditNodeIn], node_id: str | None) -> EditNodeIn | None:
    return next((n for n in arvore if n.node_id == node_id), None)


async def ultimo_user(messages: list[dict]) -> str:
    return next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")


async def rotear_alvo(
    messages: list[dict], arvore: list[EditNodeIn], foco: str | None
) -> str | None:
    if not arvore:
        return None
    if len(arvore) == 1:
        return arvore[0].node_id
    catalogo = "\n".join(f"- node_id={n.node_id} | [{n.assunto}] {n.titulo}" for n in arvore)
    ultimo = await ultimo_user(messages)
    try:
        data = await ollama_client.generate_json(
            f"Documentos:\n{catalogo}\n\nMensagem: {ultimo}", system=TARGET_SYSTEM
        )
        nid = data.get("node_id")
        if any(n.node_id == nid for n in arvore):
            return nid
    except ollama_client.LLMError:
        pass
    return foco or arvore[0].node_id


async def detectar_novo_doc(messages: list[dict], no_foco: EditNodeIn | None) -> dict | None:
    if no_foco is None:
        return None
    ultimo = await ultimo_user(messages)
    try:
        data = await ollama_client.generate_json(
            f"Documento em foco: assunto={no_foco.assunto}, titulo={no_foco.titulo}\n"
            f"Mensagem do usuário: {ultimo}",
            system=NEWDOC_SYSTEM,
        )
        if not data.get("novo"):
            return None
        nivel = data.get("nivel") if data.get("nivel") in config.NIVEIS else "iniciante"
        return {
            "assunto": slugify(str(data.get("assunto") or no_foco.assunto)),
            "titulo": str(data.get("titulo") or "Novo documento"),
            "nivel": nivel,
        }
    except ollama_client.LLMError:
        return None


async def detectar_remocao(messages: list[dict], no_foco: EditNodeIn | None) -> str | None:
    if no_foco is None or not no_foco.doc_id:
        return None
    ultimo = await ultimo_user(messages)
    try:
        data = await ollama_client.generate_json(ultimo, system=REMOCAO_SYSTEM)
        acao = str(data.get("acao", "")).strip().lower()
    except ollama_client.LLMError:
        return None
    return acao if acao in {"remover", "arquivar"} else None


async def detectar_drift(messages: list[dict], node: EditNodeIn | None) -> str | None:
    """Sinaliza deriva de assunto durante a edição, a partir da conversa (decisão B)."""
    if node is None or not node.assunto:
        return None
    ultimo = await ultimo_user(messages)
    if not ultimo.strip():
        return None
    assunto_inferido, _ = await intent.inferir_meta(node.titulo or "documento", ultimo)
    return assunto_inferido if assunto_inferido and assunto_inferido != node.assunto else None
