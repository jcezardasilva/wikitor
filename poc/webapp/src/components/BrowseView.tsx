import { api } from '../api';
import type { WikiDocument } from '../types';
import { Markdown } from './Markdown';

interface BrowseViewProps {
  doc: WikiDocument | null;
  onEdit: (doc: WikiDocument) => void;
  onEditWithAI: (doc: WikiDocument) => void;
  onRemoved: () => Promise<void>;
}

export function BrowseView({ doc, onEdit, onEditWithAI, onRemoved }: BrowseViewProps) {
  if (!doc) {
    return (
      <div className="panel">
        <div className="muted">Selecione um documento no índice.</div>
      </div>
    );
  }

  const arquivar = async () => {
    if (!confirm(`Arquivar “${doc.titulo}”? Ele sai do índice, mas pode ser restaurado.`)) return;
    await api.archiveDocument(doc.id);
    await onRemoved();
  };

  const excluir = async () => {
    if (!confirm(`Mover “${doc.titulo}” para a lixeira? Pode ser restaurado nos próximos 30 dias.`)) return;
    await api.trashDocument(doc.id);
    await onRemoved();
  };

  return (
    <div className="panel">
      <div className="doc-meta">
        assunto: <b>{doc.assunto}</b> · nível: <b>{doc.nivel}</b> · {doc.atualizado_em} ·{' '}
        <a onClick={() => onEdit(doc)}>editar</a> ·{' '}
        <a onClick={() => onEditWithAI(doc)}>editar com IA</a> ·{' '}
        <a onClick={arquivar}>arquivar</a> ·{' '}
        <a className="danger" onClick={excluir}>excluir</a>
      </div>
      <Markdown source={doc.conteudo} />
    </div>
  );
}
