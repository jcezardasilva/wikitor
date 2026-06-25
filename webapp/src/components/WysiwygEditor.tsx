import { useEffect, useRef, useState } from 'react';
import { Crepe } from '@milkdown/crepe';
import '@milkdown/crepe/theme/common/style.css';
import '@milkdown/crepe/theme/nord-dark.css';

interface Props {
  value: string; // markdown semente (não controla o editor após montar)
  onChange: (md: string) => void;
}

// Editor WYSIWYG markdown (Milkdown/Crepe). Markdown-first via remark → round-trip seguro.
// Uncontrolled internamente: `value` é só a semente inicial; alternar de doc usa `key` no pai.
export function WysiwygEditor({ value, onChange }: Props) {
  const hostRef = useRef<HTMLDivElement>(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const [erro, setErro] = useState(false);

  useEffect(() => {
    const host = hostRef.current;
    if (!host) return;

    const crepe = new Crepe({
      root: host,
      defaultValue: value,
      // Mantém só o escopo acordado (básico + código + tabelas); evita construções
      // fora de escopo que arriscariam o round-trip.
      features: {
        [Crepe.Feature.ImageBlock]: false,
        [Crepe.Feature.Latex]: false,
        [Crepe.Feature.AI]: false,
      },
    });

    crepe.on((listener) => {
      listener.markdownUpdated((_ctx, markdown) => onChangeRef.current(markdown));
    });

    crepe.create().catch(() => setErro(true));

    return () => {
      crepe.destroy().catch(() => undefined);
    };
    // Monta uma vez por instância; troca de documento é feita via `key` no componente pai.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (erro) {
    // Fallback: se o editor visual falhar, edição não fica bloqueada.
    return (
      <textarea
        className="editor-input"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  return <div ref={hostRef} className="wysiwyg-host" />;
}
