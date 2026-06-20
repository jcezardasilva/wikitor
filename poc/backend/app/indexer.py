"""Geração da cadeia de índices a partir dos frontmatters (índice é derivado).

- resumo de cada doc: gerado por LLM no momento do save (guardado no frontmatter).
- _master.json e {assunto}.json: reconstruídos a partir dos frontmatters (sem LLM).
"""
from __future__ import annotations

from . import config, llm, storage
from .models import (
    Document,
    IndexEntry,
    MasterIndex,
    MasterIndexEntry,
    SubjectIndex,
)

_RESUMO_SYSTEM = (
    "Você resume documentos técnicos em português do Brasil. "
    "Responda apenas com o resumo, em uma frase objetiva (máx. 30 palavras), sem preâmbulo."
)


async def gerar_resumo(titulo: str, conteudo: str) -> str:
    prompt = f"Título: {titulo}\n\nConteúdo:\n{conteudo[:4000]}\n\nResumo:"
    try:
        return await llm.generate(prompt, system=_RESUMO_SYSTEM)
    except llm.LLMError:
        # POC: se o LLM falhar, não bloqueia o save.
        return conteudo.strip().split("\n", 1)[0][:160]


def rebuild_indices() -> MasterIndex:
    """Reconstrói toda a cadeia de índices a partir dos documentos. O(n), tudo local."""
    docs = [d for d in storage.list_documents() if d.status == "publicado"]

    por_assunto: dict[str, list[Document]] = {}
    for d in docs:
        por_assunto.setdefault(d.assunto, []).append(d)

    master = MasterIndex()
    for assunto, items in sorted(por_assunto.items()):
        niveis: dict[str, list[IndexEntry]] = {n: [] for n in config.NIVEIS}
        for d in items:
            nivel = d.nivel if d.nivel in niveis else "iniciante"
            niveis[nivel].append(
                IndexEntry(
                    id=d.id,
                    path=f"docs/{d.id}.md",
                    titulo=d.titulo,
                    resumo=d.resumo,
                    nivel=nivel,
                )
            )
        # relacionados: heurística simples — demais assuntos (POC).
        relacionados = [a for a in por_assunto if a != assunto]
        subj = SubjectIndex(
            assunto=assunto,
            resumo=f"{len(items)} documento(s) sobre {assunto}.",
            niveis=niveis,
            relacionados=relacionados,
        )
        storage.write_index(assunto, subj.model_dump())
        master.assuntos.append(
            MasterIndexEntry(
                assunto=assunto,
                resumo=subj.resumo,
                path=f"indices/{assunto}.json",
                total_docs=len(items),
            )
        )

    storage.write_index("_master", master.model_dump())
    return master
