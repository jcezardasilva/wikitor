import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { LLMSettings } from '../types';

export interface LlmInfoState {
  info: LLMSettings | null;
  reload: () => Promise<void>;
}

// Provedor/modelo de LLM ativo, para exibir no header. Recarregável após salvar settings.
export function useLlmInfo(): LlmInfoState {
  const [info, setInfo] = useState<LLMSettings | null>(null);

  const reload = useCallback(async () => {
    const s = await api.getLlmSettings().catch(() => null);
    setInfo(s);
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { info, reload };
}
