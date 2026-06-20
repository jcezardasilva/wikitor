# Wikitor — Documento de Design

> Solução de gestão de conhecimento baseada em wiki de documentos Markdown, com
> índices gerados por LLM e consumo por humanos e agentes de IA (MCP).
> **Status:** Design validado (brainstorming). Pronto para handoff de implementação.
> **Data:** 2026-06-20

---

## 1. Understanding Summary

- **O que:** Wiki de conhecimento em **Markdown** no **Azure Storage Account**, com uma
  **cadeia de índices gerados por LLM** (Azure OpenAI) que relaciona **assuntos** e
  **níveis de conhecimento**, apontando para os documentos completos. **Sem busca vetorial.**
- **Por que:** Centralizar conhecimento consumível por **humanos** (navegação) e por
  **agentes de IA externos** (via MCP), com retrieval por navegação em índices encadeados
  e controle de acesso ponta a ponta.
- **Para quem:** Solução **multitenant**, acesso **misto** (público + restrito por grupos),
  identidade via **Microsoft Entra ID**.
- **2 modos de consumo:**
  1. **Navegação manual** em página web dedicada (front-end já existente, fora do escopo deste design).
  2. **MCP-server** consumido por plataformas de agentes de IA, autenticando o **usuário final**.
- **Modelo de dados / tenancy:** container único; **um diretório por tenant** + **metadados nos
  arquivos** (frontmatter). A **aplicação tem acesso a todos os arquivos** e **enforça permissões
  na camada de aplicação**.
- **Cadeia de índices:** duas dimensões — **profundidade** (master → assunto → documento) e
  **maturidade** (iniciante / intermediário / avançado). Atualizada por LLM a cada save.
- **Plataforma:** backend em **pods no AKS** (Content API, MCP Server, Index Generator),
  **Azure OpenAI** para gerar índices, **Key Vault** + managed identities. Infra fora do escopo.

---

## 2. Assumptions

1. Não há agente de chat Q&A hospedado por nós — a geração de respostas ocorre nas
   **plataformas externas** que consomem o MCP.
2. Controle de acesso é **sempre** na camada de aplicação (Storage acessado por identidade
   única de app), tanto na navegação quanto no MCP.
3. `tenantId` e `grupos` vêm como claims/roles no token Entra. Usuário multi-tenant informa o
   **tenant ativo** explicitamente, validado contra os claims.
4. **Performance:** leitura/navegação de doc < 1s; chamadas MCP em poucos segundos
   (latência de LLM ocorre no consumidor externo, não em nós).
5. **Reliability:** ~99% de disponibilidade; sem multi-região por ora.
6. **Segurança:** segredos no Key Vault; managed identities no AKS; tráfego LLM dentro do Azure;
   Private Endpoints quando a infra permitir.
7. **Idioma:** conteúdo majoritariamente PT-BR (configurável).
8. **Escala:** começa pequeno (MVP), arquitetura evolui para médio/grande sem reescrita.

---

## 3. Não-objetivos (explícitos)

- Provisionamento de **infraestrutura** (AKS, rede, Front Door) e o **front-end** existente.
- **Busca vetorial / embeddings.**
- Hospedar **LLM de chat próprio**.
- Tratar **conteúdo não-markdown como fonte de conhecimento** (apenas referência/anexo).

---

## 4. Decision Log

| # | Decisão | Alternativas consideradas | Por que |
|---|---------|---------------------------|---------|
| D1 | **2 modos de consumo**: navegação manual + MCP-server | Chat Q&A hospedado, busca semântica própria, REST pública | Inteligência de Q&A mora nas plataformas externas; reduz escopo e infra |
| D2 | **Sem busca vetorial**; retrieval por **cadeia de índices** | Azure AI Search, pgvector, Foundry agents | Mais simples, sem infra de vetores; navegação por índice atende o caso |
| D3 | **Índices gerados por LLM** automaticamente a cada save | Hierarquia manual, híbrido com revisão | Mantém índice atualizado sem trabalho manual; autor pode corrigir sugestão |
| D4 | **Azure OpenAI** para geração de índices | Foundry multi-modelo, API externa (Anthropic/OpenAI) | Mesma nuvem, compliance, rede privada |
| D5 | Backend em **pods no AKS** | Functions, Container Apps, SWA gerenciado | Decisão do time/plataforma existente |
| D6 | **Entra ID** para identidade | External ID (B2C), IdP externo (Okta/Auth0) | Padrão Azure; reusa grupos/roles |
| D7 | **Multitenant**: 1 container, **diretório por tenant + metadados** | Container/conta por tenant, metadados puros | Equilíbrio isolamento × simplicidade; app filtra em código |
| D8 | Controle de acesso na **camada de aplicação**; app tem acesso total ao Storage | ACL por usuário no Storage (SAS/RBAC por blob) | Multitenancy e regras ricas vivem melhor no app |
| D9 | **Abordagem A** — índices como arquivos no Storage (source-of-truth único) | B (banco de metadados), C (híbrida com projeção) | YAGNI; evolui para C se a escala exigir, sem reescrita |
| D10 | Acesso via MCP **por identidade do usuário final** (OAuth/Entra) | Credencial da plataforma, só conteúdo público | Mesma regra da navegação; máxima segurança |
| D11 | Content API e MCP como **superfícies finas** sobre **núcleo de acesso compartilhado** | Implementações independentes | Uma única regra de acesso; paridade garantida |
| D12 | Revisão **híbrida por sensibilidade**: público/crítico = portão; restrito = consultivo | Sempre portão, sempre consultivo | Equilíbrio entre segurança e agilidade |
| D13 | Revisores = **grupos Entra por assunto** (`revisores-{assunto}`) | Donos por documento, contribuidores anteriores | Reusa identidade existente; baixa manutenção |
| D14 | No portão, manter **versão publicada + proposta (.draft)** lado a lado | Sobrescrever direto | Leitor vê conteúdo aprovado enquanto revisão corre |
| D15 | Itens não autorizados são **omitidos** do índice; acesso direto retorna **404** | 403 explícito | Não vazar a existência de conteúdo restrito |
| D16 | MCP **reautoriza no `get_document`** mesmo após `search_index` filtrado | Confiar no filtro do índice | Defesa em profundidade contra path forjado |
| D17 | **`.md` = conhecimento** (indexado, servido à LLM); **demais formatos = referência** (linkados, baixáveis sob permissão, fora do índice) | Indexar anexos, OCR/extração | Fronteira nítida; evita ruído e processamento de conteúdo |
| D18 | Frontmatter é **source-of-truth**; índice é **derivado** e reconciliável | Índice como verdade | Divergência tratada como recuperável, não crítica |
| D19 | Backend em **Python (FastAPI)** para Content API, MCP Server e Index Generator | C#/.NET, Node/TypeScript | SDKs Azure maduros, SDK MCP em Python, melhor fit p/ Index Generator (LLM) |

---

## 5. Design Final

### 5.1 Modelo de dados e layout no Storage

Container único, um diretório por tenant; conteúdo, índices e anexos separados:

```
wiki-content/                      (container)
  {tenantId}/
    docs/
      {assunto}/
        introducao.md
        avancado-xyz.md
    indices/
      _master.json                 # índice raiz do tenant
      {assunto}.json               # índice por assunto
    assets/
      {assunto}/
        diagrama.pdf               # referência (não é fonte de conhecimento)
```

**Frontmatter de cada `.md`** (metadados usados para filtragem e ciclo de vida):

```yaml
---
id: doc-uuid
tenant: tenantA
assunto: redes
nivel: iniciante            # iniciante | intermediario | avancado
visibilidade: restrito       # publico | restrito
critico: false               # marca conteúdo sensível (força portão)
grupos: [eng, suporte]       # grupos Entra autorizados (se restrito)
titulo: "Introdução a Redes"
referencias: [assets/redes/diagrama.pdf]
status: publicado            # rascunho | em_revisao | publicado
revisao:
  exigida: false
  solicitada_em: null
  revisores_grupo: revisores-redes
  aprovacoes: []
atualizado_em: 2026-06-20
---
```

**Arquivo de índice por assunto (`{assunto}.json`)** — encadeia profundidade + maturidade,
referenciando docs sem duplicar o conteúdo:

```json
{
  "assunto": "redes",
  "resumo": "Conteúdos sobre redes...",
  "niveis": {
    "iniciante":     [{ "id": "doc-uuid", "path": "docs/redes/introducao.md",
                        "titulo": "...", "resumo": "...",
                        "visibilidade": "publico", "grupos": [] }],
    "intermediario": [],
    "avancado":      []
  },
  "relacionados": ["seguranca", "infraestrutura"]
}
```

O `_master.json` lista os assuntos e aponta para cada `{assunto}.json`, formando a cadeia
**master → assunto → documento**, com o nível como eixo transversal.

> Metadados ficam **tanto** no frontmatter (verdade junto ao doc) **quanto** copiados no índice
> (para o agente decidir sem abrir cada doc). O Index Generator mantém os dois sincronizados.

### 5.2 Componentes (serviços no AKS)

```
                    ┌─────────────────────────────┐
   Navegação ──────▶│  Content API (REST)         │
   (front existente)│  - lista índices/assuntos   │
                    │  - lê documento             │
                    │  - aplica filtro de acesso  │
                    └──────────────┬──────────────┘
                                   │
   Plataformas IA ───▶┌────────────▼─────────────┐   ┌──────────────┐
   (via MCP)          │  MCP Server              │──▶│   Storage    │
                      │  - tools: search_index,  │   │  (1 container│
                      │    get_document          │   │   /tenant)   │
                      │  - mesma lib de acesso   │   └──────▲───────┘
                      └──────────────────────────┘          │
                                                             │ grava índice
   Autoria/save ─────▶┌──────────────────────────┐          │
                      │  Index Generator (worker)│──────────┘
                      │  - chamado ao salvar doc │
                      │  - Azure OpenAI gera     │
                      │    resumo/nível/assunto  │
                      └──────────────────────────┘

   Núcleo compartilhado:  Access Control Lib  +  Storage Client
```

1. **Content API (REST):** serve a navegação manual.
   `GET /tenants/{t}/index`, `GET /tenants/{t}/subjects/{s}`, `GET /tenants/{t}/docs/{id}`.
2. **MCP Server:** ferramentas `search_index`, `get_document`, `list_subjects` para agentes externos.
   Reusa a mesma Access Control Lib.
3. **Index Generator:** worker disparado ao salvar/editar; chama Azure OpenAI para extrair
   resumo, sugerir `assunto`/`nivel`, e atualiza `{assunto}.json` + `_master.json`.
4. **Access Control Lib (núcleo):** dado `(identidade, tenant, ação, recurso)`, filtra índices e
   autoriza leitura. Toda via de consumo passa por ela.

### 5.3 Ciclo de vida do conteúdo e fluxo de revisão

**Regra de sensibilidade (portão vs. consultivo):**

| Conteúdo | Comportamento | Estado após edição |
|---|---|---|
| `visibilidade: publico` **ou** `critico: true` | **Portão** — aprovação obrigatória | `em_revisao` (não indexado) |
| `visibilidade: restrito` (interno) | **Consultivo** — publica já | `publicado`, sinalizado p/ revisão |

**Fluxo ao salvar uma edição:**

1. App valida permissão de **edição** (grupos do usuário ⊇ `grupos` do doc).
2. Determina o comportamento pela regra de sensibilidade.
3. **Consultivo:** grava como `publicado`, marca `revisao.solicitada`, notifica `revisores-{assunto}`;
   Index Generator atualiza o índice imediatamente.
4. **Portão:** grava como `em_revisao` (proposta `.draft`), **não** atualiza o índice público,
   notifica o grupo. Após aprovação, vira `publicado` e o índice é (re)gerado.
5. Aprovação/rejeição registrada em `revisao.aprovacoes` + histórico.
   Rejeição no portão descarta o `.draft`, mantendo a versão publicada intacta.

**Canal de notificação:** ponto em aberto (e-mail via grupo Entra ou item de "pendências de
revisão" exposto na API). O mecanismo de entrega depende da infra; o **estado/sinalização** é nosso.

### 5.4 Controle de acesso e fluxos de consumo

**Algoritmo de autorização (leitura):**

```
1. Resolver tenant do usuário  → deve == tenant do recurso (isolamento)
2. Se doc.visibilidade == publico        → permite
3. Se doc.visibilidade == restrito:
      permite SE  (grupos do usuário ∩ doc.grupos) ≠ ∅
4. Caso contrário → nega (omite do índice; 404 no acesso direto)
```

A filtragem ocorre **antes** de devolver índices — o usuário nunca vê no índice o que não pode abrir.

**Fluxo 1 — Navegação manual:** Browser →(token Entra)→ Content API → valida token, extrai
tenant+grupos → lê índices do tenant → Access Control Lib filtra → retorna índice/doc filtrado.

**Fluxo 2 — MCP:** Agente externo →(OAuth, identidade do usuário final)→ MCP Server →
mesma validação → `search_index` navega a cadeia filtrada → `get_document` **reautoriza** antes de ler
→ retorna markdown + citação (path/id). Anexos retornam apenas como links, nunca inlinados.

### 5.5 Anexos / referências não-markdown

- `.md` = **conhecimento** (indexado, servido à LLM); demais formatos = **referência**.
- Index Generator ignora não-markdown na extração; anexos entram no índice apenas como ponteiros.
- MCP `get_document` retorna markdown; anexos como links/caminhos (metadados), nunca inlinados.
- Anexo herda a permissão do doc/assunto; download passa pela Access Control Lib (sem URL pública
  direta para conteúdo restrito).

### 5.6 Tratamento de erros e casos de borda

| Situação | Content API | MCP Server |
|---|---|---|
| Token inválido/expirado | 401 | erro de auth (re-OAuth) |
| Sem permissão | **404** (não vaza existência) | "não encontrado" |
| Tenant divergente | 404 | idem |
| Índice desatualizado | serve doc; dispara reindex | idem |
| Azure OpenAI indisponível | salva doc; **enfileira** reindex | n/a |

- **Índice ausente/corrompido:** leitura de doc não depende do índice (frontmatter é a verdade);
  job de reconciliação reconstrói `{assunto}.json` a partir dos frontmatters.
- **Edição concorrente:** ETag/optimistic concurrency do Blob; gravação obsoleta falha e pede merge.
- **LLM erra assunto/nível:** sugestão é editável pelo autor antes de confirmar.
- **Mudança de assunto/nível:** entrada é movida entre índices.
- **Revisor órfão:** grupo vazio escala para fallback (`admins-{tenant}`).
- **Exclusão de doc:** remove a entrada do índice atomicamente; nunca deixa link morto.

### 5.7 Estratégia de testes

1. **Unit — Access Control Lib (prioridade máxima):** matriz
   `{publico, restrito} × {grupo correto, errado, sem grupo} × {tenant igual, diferente}`;
   itens negados omitidos dos índices; property-based (retornado ⊆ autorizado).
2. **Contrato — paridade Content API ↔ MCP:** mesmo usuário/tenant vê o mesmo conjunto nas duas
   superfícies; `get_document` nega path forjado (defesa em profundidade).
3. **Index Generator:** entrada válida (schema), idempotência, movimentação de assunto/nível,
   não-markdown nunca vira fonte.
4. **Fluxo de revisão:** híbrido correto; aprovação publica/indexa; rejeição descarta `.draft`;
   concorrência com ETag obsoleto falha previsivelmente.
5. **Reconciliação:** índice corrompido é reconstruído; nenhuma entrada aponta para path inexistente.
6. **E2E (smoke):** criar → indexar → navegar (API) → consumir (MCP) → editar → revisar →
   republicar, com 2 tenants e 2 perfis para confirmar isolamento.

---

## 6. Open Questions remanescentes

1. **Contratos do front-end existente:** a página atual já define endpoints/payloads que a Content
   API precisa respeitar? Necessário para alinhar a API de conteúdo na implementação.
2. **Canal de notificação de revisão:** e-mail via grupo Entra vs. item de pendências na API
   (depende parcialmente da infra, fora do escopo deste design).
3. **Versionamento/retenção histórica:** manter histórico de versões dos docs? (não decidido)
