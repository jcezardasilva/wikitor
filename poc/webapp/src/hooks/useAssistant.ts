import { useState } from 'react';
import { api } from '../api';
import type {
  AssistantTreeResponse,
  ChatMessage,
  EditNode,
  EditNodeWire,
  Nivel,
  NovoDocSugestao,
  SavePlan,
  SavedRef,
  SourceRef,
  TreeAcao,
  WikiDocument,
} from '../types';

export interface ChatItem {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceRef[];
  thinking?: boolean;
}

export interface AssistantState {
  items: ChatItem[];
  tree: EditNode[];
  addDocNode: (doc: WikiDocument) => void;
  send: (texto: string) => Promise<void>;
}

let counter = 0;
const nextId = () => ++counter;
const uid = () => `n${nextId()}`;
const errMsg = (e: unknown) => (e instanceof Error ? e.message : String(e));

// ---------- transformações puras da árvore ----------

function toWire(n: EditNode): EditNodeWire {
  return {
    node_id: n.nodeId,
    assunto: n.assunto,
    doc_id: n.docId,
    titulo: n.titulo,
    nivel: n.nivel,
    conteudo: n.conteudo,
    alterado: n.alterado,
  };
}

function addNode(tree: EditNode[], node: EditNode): EditNode[] {
  return [...tree.map((n) => ({ ...n, emFoco: false })), node];
}

function focusAndMark(tree: EditNode[], alvo: string, drift?: string): EditNode[] {
  return tree.map((n) =>
    n.nodeId === alvo
      ? { ...n, emFoco: true, alterado: true, driftAssunto: drift ?? n.driftAssunto }
      : { ...n, emFoco: false },
  );
}

function applySaved(tree: EditNode[], salvos: SavedRef[]): EditNode[] {
  const byNode = new Map(salvos.map((s) => [s.node_id, s]));
  const saiuDaArvore = new Set(['removido', 'arquivado', 'lixeira']);
  const removidos = new Set(
    salvos.filter((s) => s.tipo && saiuDaArvore.has(s.tipo)).map((s) => s.node_id),
  );
  return tree
    .filter((n) => !removidos.has(n.nodeId))
    .map((n) => {
      const s = byNode.get(n.nodeId);
      if (!s || s.tipo !== 'salvo') return n;
      return {
        ...n,
        docId: s.id,
        assunto: s.assunto ?? n.assunto,
        titulo: s.titulo ?? n.titulo,
        alterado: false,
        driftAssunto: undefined,
      };
    });
}

function novoNo(sug: NovoDocSugestao, alterado: boolean): EditNode {
  return {
    nodeId: uid(),
    assunto: sug.assunto,
    docId: null,
    titulo: sug.titulo,
    nivel: (sug.nivel as Nivel) || 'iniciante',
    conteudo: '',
    alterado,
    emFoco: true,
  };
}

function sourcesFromRes(res: AssistantTreeResponse): SourceRef[] | undefined {
  return res.acao === 'resposta' ? res.fontes : undefined;
}

// ---------- hook ----------

export function useAssistant(onSaved: () => Promise<void>): AssistantState {
  const [items, setItems] = useState<ChatItem[]>([]);
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [tree, setTree] = useState<EditNode[]>([]);
  const [foco, setFoco] = useState<string | null>(null);
  const [planoPendente, setPlanoPendente] = useState<SavePlan | null>(null);
  const [propostaPendente, setPropostaPendente] = useState<NovoDocSugestao | null>(null);

  const addMsg = (item: ChatItem) => setItems((prev) => [...prev, item]);

  const addDocNode = (doc: WikiDocument) => {
    const node: EditNode = {
      nodeId: uid(),
      assunto: doc.assunto,
      docId: doc.id,
      titulo: doc.titulo,
      nivel: doc.nivel,
      conteudo: doc.conteudo,
      alterado: false,
      emFoco: true,
    };
    setTree((prev) => addNode(prev, node));
    setFoco(node.nodeId);
    addMsg({
      id: nextId(),
      role: 'assistant',
      content: `Vamos trabalhar em **${doc.titulo}**. Peça mudanças ou descreva melhorias; quando quiser, é só pedir para salvar.`,
    });
  };

  const commitPlano = async (plano?: SavePlan) => {
    setPlanoPendente(null);
    if (!plano) return;
    try {
      const res = await api.commit(plano);
      setTree((t) => applySaved(t, res.salvos));
      await onSaved();
      addMsg({
        id: nextId(),
        role: 'assistant',
        content: 'Gravado.',
        sources: res.salvos.map((s) => ({ id: s.id, titulo: s.titulo ?? s.id })),
      });
    } catch (e) {
      addMsg({ id: nextId(), role: 'assistant', content: `Erro ao gravar: ${errMsg(e)}` });
    }
  };

  const inserirNo = (sug: NovoDocSugestao, alterado: boolean) => {
    const node = novoNo(sug, alterado);
    setTree((t) => addNode(t, node));
    setFoco(node.nodeId);
  };

  const handlers: Record<TreeAcao, (res: AssistantTreeResponse) => void | Promise<void>> = {
    resposta: () => {},
    autoria: (res) => {
      if (!res.alvo) return;
      setTree((t) => focusAndMark(t, res.alvo!, res.drift?.assunto_sugerido));
      setFoco(res.alvo);
    },
    novo_no_auto: () => inserirNo({ assunto: '', titulo: '', nivel: 'iniciante' }, true),
    propor_novo_doc: (res) => {
      if (res.sugestao) setPropostaPendente(res.sugestao);
    },
    criar_no: () => {
      if (propostaPendente) inserirNo(propostaPendente, false);
      setPropostaPendente(null);
    },
    plano_save: (res) => {
      if (res.plano) setPlanoPendente(res.plano);
    },
    cancelado: () => {
      setPlanoPendente(null);
      setPropostaPendente(null);
    },
    confirmado: (res) => commitPlano(res.plano),
  };

  const aplicarAcao = (res: AssistantTreeResponse) => handlers[res.acao]?.(res);

  const send = async (texto: string) => {
    const thinkingId = nextId();
    setItems((prev) => [
      ...prev,
      { id: nextId(), role: 'user', content: texto },
      { id: thinkingId, role: 'assistant', content: 'pensando…', thinking: true },
    ]);
    const nextHistory: ChatMessage[] = [...history, { role: 'user', content: texto }];
    setHistory(nextHistory);
    try {
      const res = await api.assistantTree({
        messages: nextHistory,
        modo: 'arvore',
        arvore: tree.map(toWire),
        foco,
        plano_pendente: planoPendente,
        proposta_pendente: propostaPendente,
      });
      setItems((prev) =>
        prev.map((it) =>
          it.id === thinkingId
            ? { ...it, content: res.resposta || '', sources: sourcesFromRes(res), thinking: false }
            : it,
        ),
      );
      if (res.acao !== 'confirmado') setHistory((h) => [...h, { role: 'assistant', content: res.resposta || '' }]);
      await aplicarAcao(res);
    } catch (e) {
      setItems((prev) =>
        prev.map((it) =>
          it.id === thinkingId ? { ...it, content: `Erro: ${errMsg(e)}`, thinking: false } : it,
        ),
      );
    }
  };

  return { items, tree, addDocNode, send };
}
