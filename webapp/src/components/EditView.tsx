import { useEffect, useState } from 'react';
import { api } from '../api';
import { NIVEIS, type Nivel, type WikiDocument } from '../types';
import { Markdown } from './Markdown';

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
      <h2>Edição manual</h2>
      <label>
        Título
        <input
          type="text"
          value={form.titulo}
          onChange={(e) => set({ titulo: e.target.value })}
        />
      </label>
      <div className="row">
        <label>
          Assunto
          <input
            type="text"
            value={form.assunto}
            onChange={(e) => set({ assunto: e.target.value })}
          />
        </label>
        <label>
          Nível
          <select value={form.nivel} onChange={(e) => set({ nivel: e.target.value as Nivel })}>
            {NIVEIS.map((n) => (
              <option key={n} value={n}>
                {n}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="editor-field">
        <span className="editor-label">Conteúdo (markdown)</span>
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
      </div>
      <div className="row">
        <button className="primary" onClick={handleSave}>
          Salvar (gera resumo + reindexa)
        </button>
        <button onClick={() => { setForm(EMPTY); setStatus('Novo documento'); }}>
          Novo documento
        </button>
        <span className="muted">{status}</span>
      </div>
    </div>
  );
}
