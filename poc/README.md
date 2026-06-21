# Wikitor — POC

POC da wiki de conhecimento: markdown **local** (sem Azure), LLM via **Ollama**, web **sem auth**.
Demonstra os processos básicos: **navegar/consultar**, **atualizar manualmente** e **via IA**
(geração assistida + Q&A por navegação na cadeia de índices, sem busca vetorial).

## Pré-requisitos

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) para gerenciar dependências
- Node 20+ (front-end React)
- Ollama rodando em `http://localhost:11434` com um modelo (padrão: `gemma4:e2b`)

## Como rodar

**Backend**

```powershell
cd poc\backend
make install   # uv sync (deps de prod + dev)
make run       # uvicorn app.main:app --reload --port 8000
```

**Front-end (React)** — o webapp é o front-end padrão (`poc/webapp`).

- Desenvolvimento (hot reload, proxy `/api` -> `:8000`):

  ```powershell
  cd poc\webapp
  npm install
  npm run dev    # http://localhost:5173
  ```

- Produção (servido pelo próprio FastAPI a partir de `poc/webapp/dist`):

  ```powershell
  cd poc\webapp
  npm run build  # gera dist/, que o backend serve em http://localhost:8000
  ```

Em dev, acesse http://localhost:5173; servindo o build pelo backend, http://localhost:8000.
Veja `poc/webapp/README.md` para todos os comandos (`lint`, `test`, `test:e2e`, `check`).

### Comandos de desenvolvimento (`poc/backend/Makefile`)

| Comando | O que faz |
| --- | --- |
| `make install` / `make sync` | Instala/sincroniza dependências via `uv sync` |
| `make run` | Sobe o servidor com reload |
| `make lint` | Verifica sintaxe e estilo com `ruff` |
| `make lint-fix` | Aplica as correções automáticas do `ruff` |
| `make format` | Formata o código com `ruff format` |
| `make complexity` | Analisa complexidade ciclomática com `complexipy` |
| `make test` | Roda os testes unitários com `pytest` |
| `make check` | Roda lint + complexidade + testes (gate local) |
| `make clean` | Remove caches (`__pycache__`, `.ruff_cache`, `.pytest_cache`) |

### Variáveis de ambiente (opcionais)

| Var | Default | Descrição |
|-----|---------|-----------|
| `OLLAMA_MODEL` | `gemma4:e2b` | Modelo Ollama |
| `OLLAMA_URL` | `http://localhost:11434` | Endpoint do Ollama |
| `Wikitor_CONTENT_ROOT` | `poc/content` | Pasta dos markdown/índices |

## Estrutura

```
poc/
  backend/app/      FastAPI: core, storage local, indexer (LLM), ai (assistente unificado), main
  backend/skills/   instruções estilo SKILL.md usadas como system prompt (content-authoring.md)
  content/docs/     documentos markdown (fonte da verdade)
  content/indices/  índices derivados (_master.json, {assunto}.json)
  webapp/           front-end React + Vite (Assistente IA, Navegar, Editar)
```

## Assistente IA unificado (uma conversa para tudo)

A aba **Assistente IA** é a única superfície de IA: você só conversa. A cada mensagem o
backend (`POST /api/ai/assistant`) **infere a intenção** com o LLM e roteia para:

- **perguntar** → Q&A por navegação na cadeia de índices, citando fontes;
- **autorar** → entrevista guiada por `backend/skills/content-authoring.md` (SKILL.md como
  system prompt via `/api/chat`), fazendo perguntas para contextualizar antes de escrever;
- **salvar** → quando você confirma ("pode salvar"), sintetiza o markdown, **infere assunto e
  nível**, grava o arquivo e reindexa — sem botões, tudo na conversa.

Refinamentos após salvar atualizam o mesmo documento. "Editar com IA" (link na visualização de
um doc) abre a conversa já contextualizada com o conteúdo atual.

> `SKILL.md` não é recurso nativo do Ollama — é apenas markdown de instruções usado como
> system prompt. Modelos pequenos (gemma4:e2b) seguem o roteiro e o roteamento de intenção de
> forma razoável, não perfeita; a falha de classificação é segura (nunca salva por engano).

## O que a POC cobre (e o que não cobre)

**Cobre:** cadeia de índices (master → assunto → nível) derivada a cada save; resumo por LLM;
navegação manual; edição manual (aba **Editar**); **assistente conversacional único** que
responde dúvidas (com fontes), conduz a autoria (entrevista via SKILL.md) e salva sob confirmação.

**Não cobre (do design completo):** Azure Storage, AKS, autenticação Entra, multitenancy,
controle de acesso, MCP-server, fluxo de revisão híbrido. São o passo seguinte ao validar a POC.
