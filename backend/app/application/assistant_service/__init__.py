"""Assistente unificado (responder / autorar / salvar) e o assistente ciente da árvore.

API pública do pacote: `assistente` (fluxo legado de turno único) e `assistente_arvore`
(fluxo ciente da árvore de edição, Fase 0). Os demais submódulos são detalhes internos.
"""
from .legacy import assistente
from .tree_assistant import assistente_arvore

__all__ = ["assistente", "assistente_arvore"]
