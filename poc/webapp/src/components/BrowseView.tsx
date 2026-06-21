import type { WikiDocument } from '../types';
import { Markdown } from './Markdown';

interface BrowseViewProps {
  doc: WikiDocument | null;
  onEdit: (doc: WikiDocument) => void;
  onEditWithAI: (doc: WikiDocument) => void;
}

export function BrowseView({ doc, onEdit, onEditWithAI }: BrowseViewProps) {
  if (!doc) {
    return (
      <div className="panel">
        <div className="muted">Selecione um documento no índice.</div>
      </div>
    );
  }
  return (
    <div className="panel">
      <div className="doc-meta">
        assunto: <b>{doc.assunto}</b> · nível: <b>{doc.nivel}</b> · {doc.atualizado_em} ·{' '}
        <a onClick={() => onEdit(doc)}>editar</a> ·{' '}
        <a onClick={() => onEditWithAI(doc)}>editar com IA</a>
      </div>
      <Markdown source={doc.conteudo} />
    </div>
  );
}
