import { Suspense, lazy, useEffect, useState } from 'react';
import { api } from '../api';
import { NIVEIS, type Nivel, type WikiDocument } from '../types';
import { Markdown } from './Markdown';

// Carregado sob demanda: o Crepe (ProseMirror+CodeMirror) é pesado e o modo Visual
// é opcional (padrão é markdown), então não deve entrar no bundle inicial.
const WysiwygEditor = lazy(() =>
  import('./WysiwygEditor').then((m) => ({ default: m.WysiwygEditor })),
);

type EditorKind = 'markdown' | 'wysiwyg';
const EDITOR_KIND_KEY = 'wikitor.editorKind';

function loadEditorKind(): EditorKind {
  return localStorage.getItem(EDITOR_KIND_KEY) === 'wysiwyg' ? 'wysiwyg' : 'markdown';
}

interface EditViewProps {
  seed: WikiDocument | null; // doc carregado para edição (ou null = novo)
  onSaved: (doc: WikiDocument) => void;
}

interface FormState {
  id: string;
  titulo: string;
  assunto: string;
  nivel: Nivel;
  conteudo: string;
}

const EMPTY: FormState = { id: '', titulo: '', assunto: '', nivel: 'iniciante', conteudo: '' };

function fromDoc(doc: WikiDocument | null): FormState {
  if (!doc) return EMPTY;
  return {
    id: doc.id ?? '',
    titulo: doc.titulo ?? '',
    assunto: doc.assunto ?? '',
    nivel: doc.nivel ?? 'iniciante',
    conteudo: doc.conteudo ?? '',
  };
}

export function EditView({ seed, onSaved }: EditViewProps) {
  const [form, setForm] = useState<FormState>(fromDoc(seed));
  const [status, setStatus] = useState('');
  const [editorKind, setEditorKind] = useState<EditorKind>(loadEditorKind);

  const trocarEditor = (kind: EditorKind) => {
    localStorage.setItem(EDITOR_KIND_KEY, kind);
    setEditorKind(kind);
  };

  useEffect(() => {
    setForm(fromDoc(seed));
    setStatus(seed?.id ? `Editando: ${seed.id}` : '');
  }, [seed]);

  const set = (patch: Partial<FormState>) => setForm((f) => ({ ...f, ...patch }));

  const handleSave = async () => {
    if (!form.titulo.trim() || !form.assunto.trim()) {
      setStatus('Título e assunto são obrigatórios.');
      return;
    }
    setStatus('Salvando e gerando resumo…');
    try {
      const doc = await api.saveDocument({
        id: form.id || null,
        titulo: form.titulo.trim(),
        assunto: form.assunto.trim(),
        nivel: form.nivel,
        conteudo: form.conteudo,
      });
      setStatus(`Salvo: ${doc.id}`);
      onSaved(doc);
    } catch (e) {
      setStatus(`Erro: ${e instanceof Error ? e.message : String(e)}`);
    }
  };

  return (
    <div className="panel panel-wide editview">
      <div className="meta-edit">
        <div className="meta-head">
          <input
            type="text"
            className="meta-titulo-input"
            placeholder="Título do documento"
            value={form.titulo}
            onChange={(e) => set({ titulo: e.target.value })}
          />
          <div className="edit-actions">
            {status && <span className="muted edit-status">{status}</span>}
            <button onClick={() => { setForm(EMPTY); setStatus('Novo documento'); }}>
              Novo
            </button>
            <button className="primary" onClick={handleSave}>
              Salvar
            </button>
          </div>
        </div>
        <div className="meta-sub">
          <label>
            assunto:
            <input
              type="text"
              className="meta-inline"
              placeholder="—"
              value={form.assunto}
              onChange={(e) => set({ assunto: e.target.value })}
            />
          </label>
          <span className="meta-sep">·</span>
          <label>
            nível:
            <select
              className="meta-inline"
              value={form.nivel}
              onChange={(e) => set({ nivel: e.target.value as Nivel })}
            >
              {NIVEIS.map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <div className="editor-field">
        <div className="editor-toolbar">
          <div className="editor-switch">
            <button
              className={editorKind === 'markdown' ? 'active' : ''}
              onClick={() => trocarEditor('markdown')}
            >
              Markdown
            </button>
            <button
              className={editorKind === 'wysiwyg' ? 'active' : ''}
              onClick={() => trocarEditor('wysiwyg')}
            >
              Visual
            </button>
          </div>
        </div>
        {editorKind === 'markdown' ? (
          <div className="editor-split">
            <textarea
              className="editor-input"
              value={form.conteudo}
              placeholder="# Título&#10;&#10;Escreva o conteúdo em markdown…"
              onChange={(e) => set({ conteudo: e.target.value })}
            />
            <div className="editor-preview">
              {form.conteudo.trim() ? (
                <Markdown source={form.conteudo} />
              ) : (
                <span className="muted">A pré-visualização aparece aqui.</span>
              )}
            </div>
          </div>
        ) : (
          <>
            <Suspense fallback={<div className="muted">Carregando editor visual…</div>}>
              <WysiwygEditor
                key={seed?.id ?? 'novo'}
                value={form.conteudo}
                onChange={(md) => set({ conteudo: md })}
              />
            </Suspense>
            <span className="muted editor-aviso">
              O modo Visual pode reformatar markdown avançado (HTML, notas, imagens).
            </span>
          </>
        )}
      </div>
    </div>
  );
}
