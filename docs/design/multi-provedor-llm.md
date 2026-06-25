# Design — Suporte a múltiplos provedores de LLM

> Status: **aprovado para implementação** · Data: 2026-06-24

## 1. Resumo do entendimento

- Adicionar suporte **multi-provedor de LLM** ao Wikitor: um provedor genérico
  **OpenAI-compatible** (cobre Groq, OpenRouter, LM Studio, vLLM, etc.) ao lado
  do **Ollama nativo** já existente.
- **Configuração global persistida** no servidor (single-tenant): provedor + modelo
  escolhidos valem para toda a aplicação até serem alterados.
- **Seletor no frontend** com formulário para escolher provedor, editar `base_url`/`api_key`
  e selecionar o modelo a partir de **lista dinâmica** consultada no endpoint do provedor.
- **Backend** ganha uma camada de abstração (facade `llm` + provedores) para que os 6+
  serviços que hoje chamam `ollama_client` passem a usar o provedor ativo configurado.

### Por que existe
Hoje o LLM está fixo no Ollama local. Queremos permitir provedores remotos (modelos mais
capazes) ou outras instâncias locais sem mexer em código/env e reiniciar.

### Para quem
Operador/usuário único do Wikitor (single-tenant), que administra a própria instância.

## 2. Premissas (assunções)

- **A1** — POC single-tenant, baixo volume; sem requisito de concorrência alta ou multiusuário.
- **A2** — Chamadas permanecem **não-streaming** (igual ao atual `stream: False`).
- **A3** — Persistência segue o padrão do projeto: arquivo em disco sob `content/` (`content/settings/llm.json`).
- **A4 (segurança)** — `api_key` é gravada em disco, **mascarada** ao ser retornada pela API
  (`gsk_…last4`), **nunca devolvida em texto puro**; ao salvar, valor vazio = "manter chave atual".
  Sem criptografia em disco por ora (single-tenant; risco documentado).
- **A5** — Ollama continua sendo o **default** quando não há config salva (compatibilidade retroativa).

## 3. Decision Log

| # | Decisão | Alternativas | Motivo |
|---|---------|--------------|--------|
| D1 | Provedores: Ollama nativo + **OpenAI-compatible genérico** | Adaptadores dedicados OpenAI/Anthropic/Gemini | Máxima cobertura com mínimo código |
| D2 | Escopo **global persistido** no servidor | Por-requisição; somente-leitura | Single-tenant; simplicidade |
| D3 | Credenciais **editáveis na UI**, salvas em disco | Env vars; híbrido | Flexibilidade pedida |
| D4 | Modelo via **lista dinâmica** do provedor | Texto livre; texto+validação | Melhor UX |
| D5 | Falha do provedor = **erro claro, sem fallback automático** | Fallback p/ Ollama; manter atual | Previsibilidade |
| D6 | Arquitetura **Abordagem A: facade `llm` + registry** | B (classes+DI); C (provedor único) | Menor risco, fiel ao estilo, extensível |
| D7 | `base_url` guardada **sem sufixo** de path | URL completa com `/v1` | Cada provedor anexa seu caminho |
| Q1 | Mantém **degradação heurística por-serviço** em `LLMError`; erro claro onde não há heurística | Quebrar sempre | Preserva comportamento atual de parsing de intenção |
| Q2 | "Buscar modelos" usa valores **não-salvos** do form (`POST /api/llm/models`) | GET com credencial salva | Validar antes de gravar; evita key em query/log |

## 4. Design final

### 4.1 Infra — contrato e facade

`backend/app/infrastructure/llm/base.py`
- `LLMError(RuntimeError)`.
- `LLMConfig` (dataclass frozen): `provider`, `base_url`, `model`, `api_key?`, `timeout`.
- `LLMProvider` (Protocol): `generate(prompt, system=None, as_json=False)`, `chat(messages, system=None)`, `list_models()`.

`backend/app/infrastructure/llm/__init__.py` (facade — o que os serviços importam)
- `_active_provider()` lê a config via `settings_repository` e instancia o provedor concreto.
- Expõe `generate / chat / generate_json` com **assinaturas idênticas** às do antigo `ollama_client`.
- `generate_json` (parsing tolerante a cercas ```) vive **só aqui**, reaproveitado por qualquer provedor.
- Usa `Protocol` (não ABC) p/ ficar fiel ao estilo leve do projeto.

### 4.2 Infra — provedores

`llm/ollama.py` (migração do `ollama_client` atual, comportamento inalterado)
- `generate` → `POST {base_url}/api/generate` (`format: json` quando `as_json`).
- `chat` → `POST {base_url}/api/chat`.
- `list_models` → `GET {base_url}/api/tags`.

`llm/openai_compatible.py` (novo, só `httpx`)
- `generate` é açúcar sobre chat completions; `as_json` → `response_format: {type: json_object}`.
- `chat` → `POST {base_url}/v1/chat/completions`, header `Authorization: Bearer <api_key>`.
- `list_models` → `GET {base_url}/v1/models`.
- `httpx.HTTPError` → `LLMError` com mensagem clara incluindo o provedor (D5).

### 4.3 Infra — persistência e segurança

`backend/app/infrastructure/settings_repository.py`
- `load_llm_config()` → lê `content/settings/llm.json`; ausente → default Ollama (A5).
- `save_llm_config(data)` → merge com existente; **escrita atômica** (`tmp + os.replace`).

`config.py`: adiciona `SETTINGS_DIR = CONTENT_ROOT / "settings"` e cria em `ensure_dirs()`.

`content/settings/llm.json` — runtime, **fora do git** (contém segredo).

Regra das três fronteiras (A4):
1. Domínio/infra: `api_key` em claro só em memória.
2. Saída (GET/PUT): presentation **mascara** (`gsk_…last4`); schema de saída ≠ interno.
3. Entrada (PUT): `api_key` vazia/ausente ⇒ **mantém a atual**.

### 4.4 Aplicação e API

`backend/app/application/llm_settings_service.py`
- `get_settings()`, `update_settings(data)` (valida `provider`), `list_models(cfg)`.

Serviços existentes (troca mecânica de 1 import cada): `qa_service`, `index_service`,
`authoring_service`, `assistant_service/{intent,confirmation,tree_routing}`.
`except ollama_client.LLMError` → `except llm.LLMError` (mantém degradação heurística — Q1).

`presentation/api.py` — novas rotas:
- `GET  /api/llm/settings` → `LLMSettingsOut` (key mascarada).
- `PUT  /api/llm/settings` → `LLMSettingsUpdate`, salva, retorna mascarado.
- `POST /api/llm/models` → `{provider, base_url, api_key?}` (valores não-salvos, Q2) → lista de modelos.

`presentation/schemas.py`:
- `LLMSettingsUpdate` (entrada; `api_key` opcional = manter atual).
- `LLMSettingsOut` (saída; `api_key_masked`, nunca a chave real).

### 4.5 Frontend

`webapp/src/types.ts`: `LLMProvider`, `LLMSettings`.
`webapp/src/api.ts`: `getLlmSettings`, `saveLlmSettings`, `fetchModels`.
`webapp/src/components/LLMSettings.tsx` (painel/seletor):
- Select de provedor; campos `base_url` e `api_key` (`type=password`, placeholder = máscara).
- Botão **"Buscar modelos"** → popula dropdown de modelo (D4/Q2); estados loading/erro/lista.
- Botão **"Salvar"**; campo de key vazio = mantém atual.
- Para Ollama, `api_key` oculto/desabilitado.
- **Ponto de entrada:** ícone de Configurações na `Sidebar.tsx`, integrado ao roteamento de `App.tsx`.

## 5. Riscos conhecidos

- `api_key` em texto plano no disco (sem criptografia) — aceitável p/ single-tenant; mitigado por
  `.gitignore` e máscara na API. Revisar se o projeto evoluir para multiusuário.
- `response_format: json_object` não é suportado por todos os provedores OpenAI-compat; fallback
  é o parsing tolerante da facade.

## 6. Estratégia de testes

- Unit: `settings_repository` (default, merge, key vazia mantém atual, escrita atômica).
- Unit: máscara da `api_key` (saída nunca expõe a chave real).
- Unit: `openai_compatible` parse de resposta e mapeamento de erro → `LLMError` (httpx mockado).
- Regressão: `OllamaProvider` mantém comportamento do `ollama_client` (testes existentes adaptados).
