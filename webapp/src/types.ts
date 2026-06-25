// Tipos espelhando os modelos do backend FastAPI (backend/app/domain/entities.py).

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
  session_id?: string;
}

export interface AssistantRequest {
  messages: ChatMessage[];
  contexto_doc?: string | null;
  doc_id?: string | null;
  session_id?: string | null;
}

// ---------- Modo árvore (Fase 1) ----------

export interface NovoDocSugestao {
  assunto: string;
  titulo: string;
  nivel: string;
}

export interface SavePlanItem {
  node_id: string;
  assunto: string;
  doc_id: string | null;
  arquivo: string;
  titulo: string;
  nivel: string;
  tipo: 'novo' | 'atualiza' | 'remover' | 'arquivar';
  redirecionado: boolean;
  conteudo: string;
}

export interface SavePlan {
  itens: SavePlanItem[];
}

// Nó da árvore de edição no cliente (estado de sessão).
export interface EditNode {
  nodeId: string;
  assunto: string;
  docId: string | null;
  titulo: string;
  nivel: Nivel;
  conteudo: string;
  alterado: boolean;
  emFoco: boolean;
  driftAssunto?: string;
}

// Formato enviado ao backend (snake_case).
export interface EditNodeWire {
  node_id: string;
  assunto: string;
  doc_id: string | null;
  titulo: string;
  nivel: string;
  conteudo: string;
  alterado: boolean;
}

export interface AssistantTreeRequest {
  messages: ChatMessage[];
  modo: 'arvore';
  arvore: EditNodeWire[];
  foco: string | null;
  plano_pendente: SavePlan | null;
  proposta_pendente: NovoDocSugestao | null;
  session_id: string | null;
}

export type TreeAcao =
  | 'resposta'
  | 'autoria'
  | 'novo_no_auto'
  | 'propor_novo_doc'
  | 'criar_no'
  | 'plano_save'
  | 'confirmado'
  | 'cancelado';

export interface AssistantTreeResponse {
  acao: TreeAcao;
  resposta: string;
  fontes?: SourceRef[];
  alvo?: string;
  drift?: { node_id: string; assunto_sugerido: string };
  sugestao?: NovoDocSugestao;
  plano?: SavePlan;
  session_id?: string;
}

export interface SavedRef {
  node_id: string;
  id: string;
  assunto?: string;
  titulo?: string;
  tipo?: 'salvo' | 'removido' | 'arquivado' | 'lixeira';
}

export interface TrashItem {
  id: string;
  titulo: string;
  assunto: string;
  excluido_em: string | null;
  dias: number;
  restante: number;
  elegivel: boolean;
}

export interface TrashList {
  itens: TrashItem[];
  retencao_dias: number;
}

export interface CommitResponse {
  salvos: SavedRef[];
}

// ---------- Configuração de provedor de LLM ----------

export type LLMProvider = 'ollama' | 'openai_compatible';

export interface LLMSettings {
  provider: LLMProvider;
  base_url: string;
  model: string;
  api_key_masked: string | null;
  timeout: number;
}

// Enviado ao PUT; api_key vazia = manter a atual.
export interface LLMSettingsUpdate {
  provider: LLMProvider;
  base_url: string;
  model: string;
  api_key?: string;
  timeout?: number;
}
