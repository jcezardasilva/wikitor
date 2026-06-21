import { useCallback, useState } from 'react';
import { api } from '../api';
import type { AssistantResponse, ChatMessage, SourceRef, WikiDocument } from '../types';

export interface ChatItem {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceRef[];
  thinking?: boolean;
}

interface AssistantState {
  items: ChatItem[];
  seedDoc: (doc: WikiDocument) => void;
  send: (texto: string) => Promise<void>;
}

let counter = 0;
const nextId = () => ++counter;

function sourcesFor(res: AssistantResponse): SourceRef[] | undefined {
  if (res.acao === 'resposta') return res.fontes;
  if (res.acao === 'salvo' && res.doc) return [res.doc];
  return undefined;
}

// Gerencia a conversa do assistente unificado (responder / autorar / salvar).
export function useAssistant(onSaved: () => Promise<void>): AssistantState {
  const [items, setItems] = useState<ChatItem[]>([]);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [contextoDoc, setContextoDoc] = useState<string | null>(null);
  const [docId, setDocId] = useState<string | null>(null);

  const seedDoc = useCallback((doc: WikiDocument) => {
    setHistory([]);
    setContextoDoc(doc.conteudo || null);
    setDocId(doc.id || null);
    setItems([
      {
        id: nextId(),
        role: 'assistant',
        content: `Vamos trabalhar em **${doc.titulo}**. O que você quer mudar ou melhorar? Quando estiver pronto, é só pedir para salvar.`,
      },
    ]);
  }, []);

  const afterSave = useCallback(async (res: AssistantResponse) => {
    await onSaved();
    const newId = res.doc?.id ?? docId;
    setDocId(newId);
    if (newId) {
      const novo = await api.getDocument(newId).catch(() => null);
      if (novo) setContextoDoc(novo.conteudo);
    }
  }, [docId, onSaved]);

  const send = useCallback(async (texto: string) => {
    const userMsg: ChatMessage = { role: 'user', content: texto };
    const thinkingId = nextId();
    setItems((prev) => [
      ...prev,
      { id: nextId(), role: 'user', content: texto },
      { id: thinkingId, role: 'assistant', content: 'pensando…', thinking: true },
    ]);
    const nextHistory = [...history, userMsg];
    setHistory(nextHistory);

    try {
      const res = await api.assistant({
        messages: nextHistory,
        contexto_doc: contextoDoc,
        doc_id: docId,
      });
      setItems((prev) =>
        prev.map((it) =>
          it.id === thinkingId
            ? { ...it, content: res.resposta || '', sources: sourcesFor(res), thinking: false }
            : it,
        ),
      );
      if (res.acao !== 'salvo') {
        setHistory((h) => [...h, { role: 'assistant', content: res.resposta || '' }]);
      } else {
        await afterSave(res);
      }
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      setItems((prev) =>
        prev.map((it) =>
          it.id === thinkingId ? { ...it, content: `Erro: ${msg}`, thinking: false } : it,
        ),
      );
    }
  }, [history, contextoDoc, docId, afterSave]);

  return { items, seedDoc, send };
}
