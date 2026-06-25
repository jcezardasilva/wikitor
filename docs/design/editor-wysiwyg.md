# Design — Editor markdown WYSIWYG (modo alternativo na Edição manual)

> Status: **aprovado para implementação** · Data: 2026-06-24

## 1. Resumo do entendimento

- Adicionar um **editor WYSIWYG** como **modo alternativo** na aba *Edição manual*
  ([webapp/src/components/EditView.tsx](../../webapp/src/components/EditView.tsx)),
  ao lado do editor markdown atual (textarea + preview).
- **Toggle de tipo de editor** (Markdown ⇄ Visual); a escolha é **lembrada** em
  localStorage. Padrão inicial: editor markdown atual.
- WYSIWYG suporta com fidelidade: **básico** (títulos, ênfase, listas, links, citações, HR),
  **código** (bloco com linguagem + inline) e **tabelas GFM**.
- Biblioteca escolhida: **Milkdown** (ProseMirror + remark), via o pacote pronto **Crepe**.

### Por que existe
Reduzir a barreira de edição para quem não conhece sintaxe markdown, mantendo o markdown
como formato de armazenamento.

### Para quem
Usuário único do Wikitor (single-tenant), autor de conteúdo.

## 2. Premissas (assunções)

- **A1** — Mudança **só no frontend**. Backend e formato `.md` não mudam; o save
  (`api.saveDocument`, recebe `conteudo` markdown) é o mesmo.
- **A2** — Round-trip via markdown (remark). Construções fora do escopo (HTML embutido, notas
  de rodapé, imagens) podem ser **normalizadas/reformatadas** ao passar pelo WYSIWYG — aceitável.
- **A3** — O markdown gerado pelo WYSIWYG deve renderizar igual no preview/visualização atuais
  (`marked`, GFM).
- **A4** — Conteúdo confiável (single-user); sanitização mínima.
- **A5** — Bundle cresce ao adicionar a lib (hoje ~197 KB); aceitável para a POC.
- **A6** — Sem colaboração em tempo real e sem autosave (fora de escopo).

## 3. Decision Log

| # | Decisão | Alternativas | Motivo |
|---|---------|--------------|--------|
| D1 | Editor **híbrido com toggle** markdown ⇄ WYSIWYG | WYSIWYG puro; markdown enriquecido | Flexibilidade pedida |
| D2 | Escopo: **só Edição manual**, modo alternativo | Coautoria IA; todo lugar | Menor risco |
| D3 | Recursos: **básico + código + tabelas (GFM)** | + imagens/HTML/notas | Cobre wiki técnica com round-trip seguro |
| D4 | Preferência **lembrada** (localStorage), padrão markdown | Sempre markdown; padrão WYSIWYG | UX sem surpresa inicial |
| D5 | Biblioteca **Milkdown** | TipTap; Toast UI Editor | Round-trip markdown-first (remark); React-friendly; tema custom |
| D6 | Usar o pacote **Crepe** do Milkdown | Core + plugins manuais | GFM/toolbar/tema prontos; menos código (YAGNI) |
| Q2 | Reformatação/normalização do markdown ao alternar é **aceitável** | Preservar bytes exatos | Inviável com round-trip por AST |

## 4. Design final

### 4.1 Componente WysiwygEditor
`webapp/src/components/WysiwygEditor.tsx`
```tsx
interface Props { value: string; onChange: (md: string) => void; }
```
- Monta o Crepe num `ref` de `<div>` no `useEffect` (mount/unmount), com `defaultValue = value`.
- Listener do Crepe → `onChange(getMarkdown())` a cada edição.
- **Uncontrolled internamente**: `value` é só semente inicial / re-sincronização ao alternar.
- Importa o CSS de tema do Crepe; ajustes de cor via CSS para casar com o tema escuro.
- Pacote: `@milkdown/crepe` (+ deps ProseMirror transitivas).

### 4.2 Integração no EditView
```tsx
type EditorKind = 'markdown' | 'wysiwyg';
const STORAGE_KEY = 'wikitor.editorKind';
const [editorKind, setEditorKind] = useState<EditorKind>(
  () => (localStorage.getItem(STORAGE_KEY) as EditorKind) || 'markdown',
);
const trocar = (kind: EditorKind) => { localStorage.setItem(STORAGE_KEY, kind); setEditorKind(kind); };
```
- Seletor de modo (botões **Markdown** / **Visual**) acima da área de conteúdo.
- Modo markdown → `editor-split` atual (textarea + preview). Modo visual → `<WysiwygEditor>`.
- `form.conteudo` é a **fonte única**; os dois editores leem/escrevem o mesmo campo.
- `handleSave` / `api.saveDocument` **inalterados** (A1).

### 4.3 Fluxo de dados e edge cases
- `markdown→visual`: Crepe monta com `value` como `defaultValue` (remark parseia).
- `visual→markdown`: `form.conteudo` já atualizado via `onChange`; textarea pode mostrar markdown
  reformatado (A2/Q2).
- **Vazio/novo doc:** monta com string vazia.
- **Markdown avançado fora de escopo:** pode ser normalizado; aviso discreto na UI + padrão markdown.
- **Troca de `seed`:** dar `key={seed?.id}` ao `WysiwygEditor` para remontar instância limpa.
- **Falha ao carregar o Crepe:** fallback para o textarea markdown (não bloqueia o save).
- **Performance:** `onChange` só atualiza estado local; sem debounce (YAGNI).

### 4.4 Estratégia de testes
- Vitest + Testing Library, no estilo do `EditView.test.tsx` atual.
- **Mockar o `WysiwygEditor`** (stub com `<textarea data-testid="wysiwyg">` chamando `onChange`):
  o Crepe usa ProseMirror/DOM real, instável em jsdom.
- Casos: toggle grava/recupera localStorage; default = markdown; fonte única preservada ao
  alternar; save chama `api.saveDocument` com o markdown correto em ambos os modos; fallback.
- Round-trip da lib (tabelas/código/listas markdown→visual→markdown): **checklist manual** de QA
  antes do merge; não reimplementamos testes do remark.

## 5. Riscos conhecidos
- Round-trip imperfeito em markdown avançado (fora de escopo) — mitigado por padrão markdown +
  aviso na UI.
- Peso do bundle e CSS de tema do Crepe podendo conflitar com o tema escuro — ajuste por CSS.
- Estabilidade do ProseMirror em jsdom — contornada mockando o editor nos testes.
