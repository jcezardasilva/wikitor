"""Resolução da resposta do usuário a um plano de gravação ou proposta pendente."""
from __future__ import annotations

from ...domain.entities import EditNodeIn, SavePlan
from ...infrastructure import ollama_client
from . import plan_builder, tree_routing

CONFIRM_SYSTEM = (
    "O usuário recebeu um plano de gravação e respondeu. Classifique a resposta. "
    'Responda APENAS JSON: {"decisao": "confirmar|ajustar|cancelar"}. '
    "confirmar = aceitou gravar; cancelar = não quer gravar; ajustar = quer mudar o plano."
)


async def resolver_confirmacao(messages: list[dict], plano: SavePlan,
                               arvore: list[EditNodeIn]) -> dict:
    ultimo = await tree_routing.ultimo_user(messages)
    try:
        data = await ollama_client.generate_json(ultimo, system=CONFIRM_SYSTEM)
        decisao = str(data.get("decisao", "")).strip().lower()
    except ollama_client.LLMError:
        decisao = "ajustar"  # falha segura: nunca grava sem confirmar
    if decisao == "confirmar":
        return {"acao": "confirmado", "resposta": "Gravando…", "plano": plano.model_dump()}
    if decisao == "cancelar":
        return {"acao": "cancelado", "resposta": "Ok, não vou gravar."}
    return await plan_builder.propor_plano(arvore, messages)  # ajustar: remonta da árvore atual


async def resolver_proposta(messages: list[dict]) -> dict:
    ultimo = await tree_routing.ultimo_user(messages)
    try:
        data = await ollama_client.generate_json(ultimo, system=CONFIRM_SYSTEM)
        decisao = str(data.get("decisao", "")).strip().lower()
    except ollama_client.LLMError:
        decisao = "cancelar"
    if decisao == "confirmar":
        return {"acao": "criar_no", "resposta": "Documento adicionado à árvore."}
    return {"acao": "cancelado", "resposta": "Mantendo o documento atual."}
