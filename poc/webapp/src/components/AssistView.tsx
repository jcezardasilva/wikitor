import { type KeyboardEvent, useEffect, useRef, useState } from 'react';
import type { ChatItem } from '../hooks/useAssistant';
import type { SourceRef } from '../types';
import { Markdown } from './Markdown';

interface AssistViewProps {
  items: ChatItem[];
  onSend: (texto: string) => void;
  onOpenDoc: (id: string) => void;
}

function Sources({ fontes, onOpenDoc }: { fontes: SourceRef[]; onOpenDoc: (id: string) => void }) {
  return (
    <div className="msg-sources">
      <span className="muted">Fontes:</span>{' '}
      {fontes.map((f) => (
        <button key={f.id} className="source-chip" onClick={() => onOpenDoc(f.id)}>
          {f.titulo}
        </button>
      ))}
    </div>
  );
}

function Message({ item, onOpenDoc }: { item: ChatItem; onOpenDoc: (id: string) => void }) {
  const cls = `msg ${item.role}${item.thinking ? ' thinking' : ''}`;
  if (item.role === 'user' || item.thinking) {
    return <div className={cls}>{item.content}</div>;
  }
  return (
    <div className={cls}>
      <Markdown source={item.content} />
      {item.sources?.length ? <Sources fontes={item.sources} onOpenDoc={onOpenDoc} /> : null}
    </div>
  );
}

const MAX_TEXTAREA_PX = 200;

export function AssistView({ items, onSend, onOpenDoc }: AssistViewProps) {
  const [text, setText] = useState('');
  const logRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = logRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [items]);

  // Auto-grow: ajusta a altura ao conteúdo até um teto, depois rola.
  const autoGrow = () => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_PX)}px`;
  };

  useEffect(autoGrow, [text]);

  const submit = () => {
    const t = text.trim();
    if (!t) return;
    setText('');
    onSend(t);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter envia; Shift+Enter quebra linha.
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="panel chatview">
      <div className="chatlog" ref={logRef}>
        {items.length === 0 ? (
          <div className="chat-empty muted">
            Converse com o assistente.
            <br />
            Pergunte sobre a wiki ou peça para criar/editar um documento — ele conduz tudo e salva
            quando você confirmar.
          </div>
        ) : (
          items.map((it) => <Message key={it.id} item={it} onOpenDoc={onOpenDoc} />)
        )}
      </div>
      <div className="chat-inputbar">
        <textarea
          ref={inputRef}
          rows={1}
          value={text}
          placeholder="Pergunte algo ou peça para documentar um assunto…  (Enter envia · Shift+Enter quebra linha)"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button className="primary" onClick={submit}>
          Enviar
        </button>
      </div>
    </div>
  );
}
