import { act, renderHook } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../api';
import type { WikiDocument } from '../types';
import { useAssistant } from './useAssistant';

const doc: WikiDocument = {
  id: 'redes/osi',
  titulo: 'OSI',
  assunto: 'redes',
  nivel: 'iniciante',
  resumo: '',
  status: 'publicado',
  referencias: [],
  atualizado_em: '2026-06-20',
  conteudo: '# OSI',
};

afterEach(() => vi.restoreAllMocks());

describe('useAssistant (modo árvore)', () => {
  it('addDocNode adiciona o documento à árvore, em foco', () => {
    const { result } = renderHook(() => useAssistant(async () => {}));
    act(() => result.current.addDocNode(doc));
    expect(result.current.tree).toHaveLength(1);
    expect(result.current.tree[0]).toMatchObject({
      docId: 'redes/osi',
      assunto: 'redes',
      titulo: 'OSI',
      emFoco: true,
      alterado: false,
    });
  });

  it('um turno de autoria marca o nó-alvo como alterado', async () => {
    const { result } = renderHook(() => useAssistant(async () => {}));
    act(() => result.current.addDocNode(doc));
    const nodeId = result.current.tree[0].nodeId;
    vi.spyOn(api, 'assistantTree').mockResolvedValue({
      acao: 'autoria',
      resposta: 'atualizei',
      alvo: nodeId,
    });
    await act(async () => {
      await result.current.send('melhora a seção de camadas');
    });
    expect(result.current.tree[0].alterado).toBe(true);
  });

  it('confirmado grava o plano e reflete o salvamento na árvore', async () => {
    const onSaved = vi.fn().mockResolvedValue(undefined);
    const { result } = renderHook(() => useAssistant(onSaved));
    act(() => result.current.addDocNode(doc));
    const nodeId = result.current.tree[0].nodeId;
    vi.spyOn(api, 'assistantTree').mockResolvedValue({
      acao: 'confirmado',
      resposta: 'Gravando…',
      plano: { itens: [] },
    });
    const commitSpy = vi.spyOn(api, 'commit').mockResolvedValue({
      salvos: [{ node_id: nodeId, id: 'redes/osi', assunto: 'redes', titulo: 'OSI' }],
    });
    await act(async () => {
      await result.current.send('confirmo');
    });
    expect(commitSpy).toHaveBeenCalled();
    expect(onSaved).toHaveBeenCalled();
    expect(result.current.tree[0]).toMatchObject({ docId: 'redes/osi', alterado: false });
  });

  it('um commit de remoção (lixeira) tira o nó da árvore', async () => {
    const { result } = renderHook(() => useAssistant(async () => {}));
    act(() => result.current.addDocNode(doc));
    const nodeId = result.current.tree[0].nodeId;
    vi.spyOn(api, 'assistantTree').mockResolvedValue({
      acao: 'confirmado',
      resposta: 'Movendo para a lixeira…',
      plano: { itens: [] },
    });
    vi.spyOn(api, 'commit').mockResolvedValue({
      salvos: [{ node_id: nodeId, id: 'redes/osi', tipo: 'lixeira' }],
    });
    await act(async () => {
      await result.current.send('confirmo');
    });
    expect(result.current.tree).toHaveLength(0);
  });
});
