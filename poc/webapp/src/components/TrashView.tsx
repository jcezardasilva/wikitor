import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { TrashItem } from '../types';

function TrashRow({
  item,
  onRestore,
  onPurge,
}: {
  item: TrashItem;
  onRestore: (id: string) => void;
  onPurge: (item: TrashItem) => void;
}) {
  return (
    <div className="trash-row">
      <div className="trash-info">
        <span className="trash-titulo">{item.titulo}</span>
        <span className="muted">
          {item.assunto} · excluído em {item.excluido_em}
        </span>
      </div>
      <span className="muted trash-restante">
        {item.elegivel ? 'pronto para excluir' : `faltam ${item.restante} dia(s)`}
      </span>
      <button onClick={() => onRestore(item.id)}>Restaurar</button>
      <button className="danger-btn" disabled={!item.elegivel} onClick={() => onPurge(item)}>
        Excluir definitivamente
      </button>
    </div>
  );
}

// Lixeira: documentos excluídos ficam aqui na retenção; só após ela a exclusão é definitiva.
export function TrashView({ onChanged }: { onChanged: () => Promise<void> }) {
  const [itens, setItens] = useState<TrashItem[]>([]);
  const [retencao, setRetencao] = useState(30);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    const t = await api.listTrash().catch(() => ({ itens: [], retencao_dias: 30 }));
    setItens(t.itens);
    setRetencao(t.retencao_dias);
    setLoading(false);
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  const restaurar = async (id: string) => {
    await api.restoreFromTrash(id);
    await reload();
    await onChanged();
  };

  const excluir = async (item: TrashItem) => {
    if (!confirm(`Excluir definitivamente “${item.titulo}”? Esta ação não pode ser desfeita.`)) return;
    await api.purgeDocument(item.id);
    await reload();
  };

  if (loading) {
    return (
      <div className="panel">
        <div className="muted">Carregando lixeira…</div>
      </div>
    );
  }
  return (
    <div className="panel">
      <h2>Lixeira</h2>
      <p className="muted">
        Itens excluídos ficam aqui por {retencao} dias e podem ser restaurados. A exclusão
        definitiva só é liberada após esse período.
      </p>
      {itens.length === 0 ? (
        <div className="muted">A lixeira está vazia.</div>
      ) : (
        <div className="trash-list">
          {itens.map((it) => (
            <TrashRow key={it.id} item={it} onRestore={restaurar} onPurge={excluir} />
          ))}
        </div>
      )}
    </div>
  );
}
