// Tipos espelhando os modelos do backend FastAPI (poc/backend/app/models.py).

export type Nivel = 'iniciante' | 'intermediario' | 'avancado';

export const NIVEIS: Nivel[] = ['iniciante', 'intermediario', 'avancado'];

export interface MasterIndexEntry {
  assunto: string;
  resumo: string;
  path: string;
  total_docs: number;
}

export interface MasterIndex {
  assuntos: MasterIndexEntry[];
}

export interface IndexEntry {
  id: string;
  path: string;
  titulo: string;
  resumo: string;
  nivel: string;
}

export interface SubjectIndex {
  assunto: string;
  resumo: string;
  niveis: Record<string, IndexEntry[]>;
  relacionados: string[];
}

export interface WikiDocument {
  id: string;
  titulo: string;
  assunto: string;
  nivel: Nivel;
  resumo: string;
  status: string;
  referencias: string[];
  atualizado_em: string;
  conteudo: string;
}

export interface SaveDocRequest {
  id?: string | null;
  titulo: string;
  assunto: string;
  conteudo: string;
  nivel?: Nivel | null;
  gerar_resumo?: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface SourceRef {
  id: string;
  titulo: string;
}

export type AssistantAcao = 'resposta' | 'autoria' | 'salvo';

export interface AssistantResponse {
  acao: AssistantAcao;
  resposta: string;
  fontes?: SourceRef[];
  doc?: SourceRef;
}

export interface AssistantRequest {
  messages: ChatMessage[];
  contexto_doc?: string | null;
  doc_id?: string | null;
}
