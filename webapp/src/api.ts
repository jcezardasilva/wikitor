// Cliente HTTP fino para a API da POC. Mantém o mesmo contrato do app.js vanilla.
import type {
  AssistantRequest,
  AssistantResponse,
  AssistantTreeRequest,
  AssistantTreeResponse,
  CommitResponse,
  LLMSettings,
  LLMSettingsUpdate,
  MasterIndex,
  SaveDocRequest,
  SavePlan,
  SubjectIndex,
  TrashList,
  WikiDocument,
} from './types';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (!res.ok) {
    const body = (await res.json().catch(() => ({}))) as { detail?: string };
    throw new Error(body.detail || res.statusText);
  }
  return res.json() as Promise<T>;
}

function jsonPost<T>(path: string, payload: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export const api = {
  getIndex: () => request<MasterIndex>('/api/index'),
  getSubject: (assunto: string) =>
    request<SubjectIndex>(`/api/subjects/${encodeURIComponent(assunto)}`),
  getDocument: (id: string) => request<WikiDocument>(`/api/docs/${id}`),
  saveDocument: (req: SaveDocRequest) => jsonPost<WikiDocument>('/api/docs', req),
  assistant: (req: AssistantRequest) =>
    jsonPost<AssistantResponse>('/api/ai/assistant', req),
  assistantTree: (req: AssistantTreeRequest) =>
    jsonPost<AssistantTreeResponse>('/api/ai/assistant', req),
  commit: (plano: SavePlan) =>
    jsonPost<CommitResponse>('/api/docs/commit', { plano }),
  archiveDocument: (id: string) =>
    request<{ ok: boolean }>(`/api/docs/${id}/archive`, { method: 'POST' }),
  // Excluir = mover para a lixeira (recuperável).
  trashDocument: (id: string) =>
    request<{ ok: boolean }>(`/api/docs/${id}/trash`, { method: 'POST' }),
  listTrash: () => request<TrashList>('/api/trash'),
  restoreFromTrash: (id: string) =>
    request<{ ok: boolean }>(`/api/trash/${id}/restore`, { method: 'POST' }),
  purgeDocument: (id: string) =>
    request<{ ok: boolean }>(`/api/trash/${id}`, { method: 'DELETE' }),
  getLlmSettings: () => request<LLMSettings>('/api/llm/settings'),
  saveLlmSettings: (req: LLMSettingsUpdate) =>
    request<LLMSettings>('/api/llm/settings', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    }),
  fetchModels: (provider: string, base_url: string, api_key?: string) =>
    jsonPost<{ models: string[] }>('/api/llm/models', { provider, base_url, api_key }),
};
