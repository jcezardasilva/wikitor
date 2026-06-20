# Wikitor — Plano de Implementação

> Derivado de [wikitor-design.md](wikitor-design.md). Stack: **Python (FastAPI)**.
> Princípio: **incremental, núcleo de acesso primeiro**, testável em cada fase.
> **Status:** Plano aprovado, aguardando início de implementação.

---

## Princípios do plano

- **Access Control Lib primeiro** — é o componente de maior risco (vazamento multitenant) e
  dependência de todas as superfícies. Construído e testado antes de API/MCP.
- **Frontmatter é a verdade**; índice é derivado. Implementar leitura por frontmatter antes do índice.
- **Superfícies finas**: Content API e MCP reusam o mesmo núcleo (lib compartilhada).
- Cada fase entrega algo **testável e demonstrável** (com 2 tenants / 2 perfis).
- Infra (AKS, rede, Key Vault) e front-end **fora do escopo** — assume-se que existem/serão providos.

---

## Estrutura de repositório (proposta)

```
wikitor/
  src/
    core/                      # núcleo compartilhado
      access_control.py        # Access Control Lib
      storage_client.py        # wrapper Azure Blob (identidade única de app)
      models.py                # Frontmatter, IndexEntry, SubjectIndex, MasterIndex (pydantic)
      frontmatter.py           # parse/serialize do frontmatter .md
      identity.py              # extração de tenant+grupos do token Entra
    content_api/               # FastAPI REST (navegação manual)
      main.py
      routes.py
    mcp_server/                # MCP server (agentes externos)
      server.py                # tools: list_subjects, search_index, get_document
    index_generator/           # worker de geração de índice
      generator.py             # chamada Azure OpenAI + atualização de índices
      reconciler.py            # job de reconciliação índice↔frontmatter
  tests/
    unit/
    contract/
    e2e/
  docs/design/
  pyproject.toml
```

---

## Fases

### Fase 0 — Fundação e modelos (esqueleto)
- `pyproject.toml`, deps: `fastapi`, `pydantic`, `azure-storage-blob`, `azure-identity`,
  `openai` (Azure), `mcp`, `pytest`.
- `core/models.py`: modelos pydantic — `Frontmatter`, `IndexEntry`, `SubjectIndex`, `MasterIndex`.
- `core/frontmatter.py`: parse/serialize de frontmatter YAML em `.md`.
- **Entregável:** schemas validados + testes de (de)serialização.

### Fase 1 — Núcleo de acesso e storage (maior prioridade de risco)
- `core/storage_client.py`: leitura/escrita de blobs por tenant (managed identity); ETag/optimistic
  concurrency; listagem por prefixo.
- `core/identity.py`: extração de `tenantId` + `grupos` do token Entra; tenant ativo explícito.
- `core/access_control.py`: algoritmo de autorização (isolamento de tenant, publico/restrito por
  grupos, omissão de itens negados).
- **Testes (prioridade máxima):** matriz completa
  `{publico, restrito} × {grupo ok, errado, sem grupo} × {tenant igual, diferente}` +
  property-based (retornado ⊆ autorizado).
- **Entregável:** lib de acesso 100% testada, isolada de API/MCP.

### Fase 2 — Content API (navegação manual)
- `content_api`: `GET /tenants/{t}/index`, `/subjects/{s}`, `/docs/{id}`.
- Integração com `access_control` (filtragem antes de retornar; 404 para negado/tenant divergente).
- Servir anexos sob autorização (sem URL pública direta).
- **Entregável:** API navegável que respeita permissões; testes de integração.

### Fase 3 — Index Generator
- `index_generator/generator.py`: ao salvar doc, chama Azure OpenAI → resumo, `assunto`, `nivel`;
  atualiza `{assunto}.json` + `_master.json`; ignora não-markdown (só ponteiros).
- Idempotência + movimentação entre assuntos/níveis.
- Sugestão do LLM **editável** pelo autor antes de confirmar.
- Resiliência: Azure OpenAI indisponível → enfileira reindex (retry).
- `index_generator/reconciler.py`: reconstrói índices a partir dos frontmatters.
- **Entregável:** índices gerados/atualizados automaticamente; testes de idempotência e reconciliação.

### Fase 4 — Fluxo de edição e revisão
- Endpoint de save com validação de permissão de edição.
- Regra de sensibilidade (portão vs. consultivo); estados `rascunho/em_revisao/publicado`.
- Portão: versão `.draft` + versão publicada lado a lado; aprovação publica e indexa; rejeição descarta draft.
- Consultivo: publica + sinaliza; notifica `revisores-{assunto}` (canal: stub/abstração — ver Q aberta).
- Revisor órfão → fallback `admins-{tenant}`.
- **Entregável:** ciclo de vida completo; testes do fluxo híbrido e de concorrência (ETag).

### Fase 5 — MCP Server
- `mcp_server/server.py`: tools `list_subjects`, `search_index`, `get_document`.
- OAuth/identidade do usuário final; reusa `access_control`; **reautoriza no `get_document`**.
- Anexos como links, nunca inlinados.
- **Testes de contrato:** paridade Content API ↔ MCP (mesmo conjunto autorizado); path forjado negado.
- **Entregável:** MCP consumível por plataforma de agentes, com paridade de acesso comprovada.

### Fase 6 — E2E e endurecimento
- Smoke E2E: criar → indexar → navegar → consumir (MCP) → editar → revisar → republicar,
  com 2 tenants e 2 perfis.
- Revisão de segurança do isolamento multitenant.
- **Entregável:** suíte E2E verde; checklist de segurança.

---

## Dependências externas a confirmar antes/durante a implementação

1. **Contratos do front-end existente** (endpoints/payloads que a Content API deve respeitar) — Fase 2.
2. **Canal de notificação de revisão** (e-mail via grupo Entra vs. item de pendências) — Fase 4.
3. **App registration no Entra** (claims de tenant/grupos; OAuth do MCP) — Fases 1 e 5.
4. **Deployment/recurso Azure OpenAI** + Storage Account com managed identity — Fases 1 e 3.
5. **Decisão sobre versionamento/retenção histórica** (open question) — impacta Fases 3 e 4.

---

## Ordem recomendada e justificativa

`Fase 0 → 1 → 2 → 3 → 4 → 5 → 6`

O núcleo de acesso (Fase 1) é o maior risco e dependência de tudo; vem cedo e totalmente testado.
A Content API (Fase 2) valida o núcleo end-to-end com a superfície mais simples. Índices (Fase 3)
e revisão (Fase 4) constroem a autoria. O MCP (Fase 5) vem por último entre as superfícies, mas
reusa todo o núcleo já endurecido, com testes de paridade garantindo que agentes externos enxergam
exatamente as mesmas permissões que a navegação.
