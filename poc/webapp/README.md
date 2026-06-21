# Wikitor — Webapp (React)

Reconstrução do front-end da POC (antes vanilla JS em `poc/web/`) usando o stack padrão
do time: **React + TypeScript + Vite**, com ESLint (regras de complexidade), Vitest e
Playwright.

Consome a mesma API do backend FastAPI (`poc/backend`), sem mudanças no contrato.

## Pré-requisitos

- Node 20+
- Backend rodando (`cd poc/backend && make run`), por padrão em `http://localhost:8000`.

## Comandos

```bash
npm install         # instala dependências
npm run dev         # servidor de dev (Vite) em http://localhost:5173, com proxy /api -> :8000
npm run lint        # ESLint (sonarjs + complexity)
npm run test        # testes unitários/componente (Vitest)
npm run test:e2e    # testes end-to-end (Playwright, backend mockado)
npm run build       # type-check + build de produção em dist/
npm run check       # gate mínimo antes de commit: lint + test + build
```

A URL da API pode ser sobrescrita em dev via `WIKITOR_API` (ex.: `WIKITOR_API=http://localhost:9000 npm run dev`).

## Estrutura

```
src/
  api.ts                 cliente HTTP da API da POC
  types.ts               tipos espelhando os modelos do backend
  markdown.ts            render markdown (marked)
  App.tsx                orquestra abas, índice e estado compartilhado
  hooks/
    useWikiIndex.ts      carrega índice mestre + índices por assunto
    useAssistant.ts      conversa do assistente (responder/autorar/salvar)
  components/
    Sidebar.tsx          índice navegável (assunto > nível > documento)
    BrowseView.tsx       leitura do documento renderizado
    EditView.tsx         edição manual (salva + reindexa)
    AssistView.tsx       chat do assistente IA
    Markdown.tsx         wrapper de renderização
e2e/                     testes Playwright (golden path)
```

## Convenções de qualidade

- Complexidade cognitiva máx. 15 (`sonarjs/cognitive-complexity`) e ciclomática máx. 10
  (`complexity`) — componentes grandes são quebrados em subcomponentes/hooks.
- `npm run check` é o gate antes de PR.
