import { marked } from 'marked';

// Renderização síncrona de markdown -> HTML para uso em dangerouslySetInnerHTML.
// O conteúdo vem do próprio backend da wiki (confiável na POC).
export function renderMarkdown(src: string): string {
  return marked.parse(src ?? '', { async: false });
}
