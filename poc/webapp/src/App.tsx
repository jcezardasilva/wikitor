import { useCallback, useState } from 'react';
import { api } from './api';
import { AssistView } from './components/AssistView';
import { BrowseView } from './components/BrowseView';
import { EditView } from './components/EditView';
import { Sidebar } from './components/Sidebar';
import { TrashView } from './components/TrashView';
import { useAssistant } from './hooks/useAssistant';
import { useWikiIndex } from './hooks/useWikiIndex';
import type { WikiDocument } from './types';

type View = 'assist' | 'browse' | 'edit' | 'trash';

const TABS: { key: View; label: string }[] = [
  { key: 'assist', label: 'Assistente IA' },
  { key: 'browse', label: 'Navegar' },
  { key: 'edit', label: 'Editar' },
  { key: 'trash', label: 'Lixeira' },
];

export function App() {
  const index = useWikiIndex();
  const [view, setView] = useState<View>('assist');
  const [browseDoc, setBrowseDoc] = useState<WikiDocument | null>(null);
  const [editSeed, setEditSeed] = useState<WikiDocument | null>(null);

  const assistant = useAssistant(index.reload);

  const openDoc = useCallback(async (id: string) => {
    const doc = await api.getDocument(id).catch(() => null);
    if (!doc) return;
    setBrowseDoc(doc);
    setView('browse');
  }, []);

  const editDoc = useCallback((doc: WikiDocument) => {
    setEditSeed(doc);
    setView('edit');
  }, []);

  const editWithAI = useCallback((doc: WikiDocument) => {
    assistant.addDocNode(doc);
    setView('assist');
  }, [assistant]);

  const onSaved = useCallback(async (doc: WikiDocument) => {
    await index.reload();
    await openDoc(doc.id);
  }, [index, openDoc]);

  const onRemoved = useCallback(async () => {
    setBrowseDoc(null);
    await index.reload();
  }, [index]);

  return (
    <>
      <header className="app-header">
        <h1>
          Wikitor <span className="tag">POC</span>
        </h1>
        <nav>
          {TABS.map((t) => (
            <button
              key={t.key}
              className={view === t.key ? 'active' : ''}
              onClick={() => setView(t.key)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="app-main">
        <Sidebar
          subjects={index.subjects}
          loading={index.loading}
          error={index.error}
          onOpenDoc={openDoc}
        />
        <section className="content">
          {view === 'assist' && (
            <AssistView
              items={assistant.items}
              tree={assistant.tree}
              onSend={assistant.send}
              onOpenDoc={openDoc}
            />
          )}
          {view === 'browse' && (
            <BrowseView
              doc={browseDoc}
              onEdit={editDoc}
              onEditWithAI={editWithAI}
              onRemoved={onRemoved}
            />
          )}
          {view === 'edit' && <EditView seed={editSeed} onSaved={onSaved} />}
          {view === 'trash' && <TrashView onChanged={index.reload} />}
        </section>
      </main>
    </>
  );
}
