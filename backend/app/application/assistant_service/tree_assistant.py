"""Assistente ciente da árvore de edição (Fase 0): orquestra os submódulos do pacote.

Propõe — nunca grava (isso é o `document_service.commit_plan`, acionado por `/api/docs/commit`).
"""
from __future__ import annotations

from ...domain.entities import EditNodeIn, NovoDocSugestao, SavePlan
from .. import authoring_service, qa_service
from . import confirmation, intent, plan_builder, tree_routing


async def _autorar_em_novo(messages: list[dict]) -> dict:
    """Árvore vazia / sem foco: não há arquivo a proteger, então cria um nó de trabalho."""
    resposta = await authoring_service.coautoria_chat(messages, contexto_doc=None)
    return {
        "acao": "novo_no_auto",
        "resposta": resposta,
        "sugestao": {"assunto": "", "titulo": "", "nivel": "iniciante"},
    }


async def assistente_arvore(messages: list[dict], arvore: list[EditNodeIn], foco: str | None,
                            plano_pendente: SavePlan | None,
                            proposta_pendente: NovoDocSugestao | None) -> dict:
    """Turno do assistente ciente da árvore. Propõe — nunca grava (isso é o /docs/commit)."""
    if plano_pendente is not None:
        return await confirmation.resolver_confirmacao(messages, plano_pendente, arvore)
    if proposta_pendente is not None:
        return await confirmation.resolver_proposta(messages)

    intencao = await intent.classificar_intencao(messages)
    if intencao == "perguntar":
        pergunta = await tree_routing.ultimo_user(messages)
        res = await qa_service.perguntar(pergunta)
        return {"acao": "resposta", "resposta": res["resposta"], "fontes": res["fontes"]}
    if intencao == "salvar":
        return await plan_builder.propor_plano(arvore, messages)

    no_foco = tree_routing.no(arvore, foco)
    if no_foco is None:
        return await _autorar_em_novo(messages)  # nada a proteger: cria nó de trabalho

    remocao = await tree_routing.detectar_remocao(messages, no_foco)
    if remocao:
        return plan_builder.plano_remocao(no_foco, remocao)

    sugestao = await tree_routing.detectar_novo_doc(messages, no_foco)
    if sugestao:
        return {
            "acao": "propor_novo_doc",
            "resposta": f"Isso parece um novo documento (assunto: {sugestao['assunto']}). Criar?",
            "sugestao": sugestao,
        }

    alvo = await tree_routing.rotear_alvo(messages, arvore, foco)
    no_alvo = tree_routing.no(arvore, alvo) or no_foco
    resposta = await authoring_service.coautoria_chat(
        messages, contexto_doc=no_alvo.conteudo or None
    )
    out = {"acao": "autoria", "alvo": no_alvo.node_id, "resposta": resposta}
    drift = await tree_routing.detectar_drift(messages, no_alvo)
    if drift:
        out["drift"] = {"node_id": no_alvo.node_id, "assunto_sugerido": drift}
    return out
