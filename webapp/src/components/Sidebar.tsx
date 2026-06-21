import { NIVEIS, type SubjectIndex } from '../types';

interface SidebarProps {
  subjects: SubjectIndex[];
  loading: boolean;
  error: string | null;
  onOpenDoc: (id: string) => void;
}

function SubjectBlock({
  subject,
  onOpenDoc,
}: {
  subject: SubjectIndex;
  onOpenDoc: (id: string) => void;
}) {
  const total = NIVEIS.reduce((n, nivel) => n + (subject.niveis[nivel]?.length ?? 0), 0);
  return (
    <div className="subject">
      <div className="s-title">
        {subject.assunto} <span className="muted">({total})</span>
      </div>
      {NIVEIS.map((nivel) => {
        const items = subject.niveis[nivel] ?? [];
        if (!items.length) return null;
        return (
          <div key={nivel}>
            <div className="nivel-label">{nivel}</div>
            {items.map((it) => (
              <button
                key={it.id}
                className="doc-link"
                title={it.resumo}
                onClick={() => onOpenDoc(it.id)}
              >
                {it.titulo}
              </button>
            ))}
          </div>
        );
      })}
    </div>
  );
}

export function Sidebar({ subjects, loading, error, onOpenDoc }: SidebarProps) {
  if (loading) return <aside className="sidebar"><div className="muted">Carregando índice…</div></aside>;
  if (error) return <aside className="sidebar"><div className="muted">Erro: {error}</div></aside>;
  if (!subjects.length) {
    return <aside className="sidebar"><div className="muted">Wiki vazia. Crie um documento.</div></aside>;
  }
  return (
    <aside className="sidebar">
      {subjects.map((s) => (
        <SubjectBlock key={s.assunto} subject={s} onOpenDoc={onOpenDoc} />
      ))}
    </aside>
  );
}
