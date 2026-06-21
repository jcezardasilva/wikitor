// Cliente HTTP fino para a API da POC. Mantém o mesmo contrato do app.js vanilla.
import type {
  AssistantRequest,
  AssistantResponse,
  MasterIndex,
  SaveDocRequest,
  SubjectIndex,
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
};
