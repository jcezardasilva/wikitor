import { renderMarkdown } from '../markdown';

// Renderiza markdown confiável (vindo do backend da wiki) como HTML.
export function Markdown({ source }: { source: string }) {
  return (
    <div
      className="rendered"
      dangerouslySetInnerHTML={{ __html: renderMarkdown(source) }}
    />
  );
}
