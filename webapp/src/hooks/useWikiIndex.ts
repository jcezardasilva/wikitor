import { useCallback, useEffect, useState } from 'react';
import { api } from '../api';
import type { SubjectIndex } from '../types';

export interface WikiIndexState {
  subjects: SubjectIndex[];
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
}

// Carrega o índice mestre e, para cada assunto, o índice detalhado (níveis/docs).
export function useWikiIndex(): WikiIndexState {
  const [subjects, setSubjects] = useState<SubjectIndex[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const master = await api.getIndex();
      const detalhes = await Promise.all(
        master.assuntos.map((a) => api.getSubject(a.assunto)),
      );
      setSubjects(detalhes);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { subjects, loading, error, reload };
}
