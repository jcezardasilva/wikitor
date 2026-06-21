import type { EditNode } from '../types';

function estadoDe(n: EditNode): { label: string; cls: string } {
  if (n.docId === null) return { label: 'novo', cls: 'novo' };
  if (n.alterado) return { label: 'alterado', cls: 'alterado' };
  return { label: 'intocado', cls: 'intocado' };
}

function agrupar(tree: EditNode[]): [string, EditNode[]][] {
  const grupos = new Map<string, EditNode[]>();
  for (const n of tree) {
    const chave = n.assunto || '(sem assunto)';
    const lista = grupos.get(chave);
    if (lista) lista.push(n);
    else grupos.set(chave, [n]);
  }
  return [...grupos.entries()];
}

function NodeRow({ node }: { node: EditNode }) {
  const estado = estadoDe(node);
  return (
    <div className={`tree-node${node.emFoco ? ' em-foco' : ''}`}>
      <span className="tree-titulo">{node.titulo || '(novo documento)'}</span>
      <span className={`tree-badge ${estado.cls}`}>{estado.label}</span>
      {node.driftAssunto ? (
        <span className="tree-drift" title="O conteúdo parece ter migrado de assunto">
          ⚠ parece ser de “{node.driftAssunto}”
        </span>
      ) : null}
    </div>
  );
}

// Árvore de documentos em edição, agrupada por índice (assunto). A IA infere o alvo
// (nó em foco) e o usuário confere visualmente aqui.
export function EditTree({ tree }: { tree: EditNode[] }) {
  if (!tree.length) return null;
  return (
    <div className="edit-tree">
      <div className="edit-tree-label">Documentos em edição</div>
      {agrupar(tree).map(([assunto, nos]) => (
        <div key={assunto} className="tree-group">
          <div className="tree-assunto">{assunto}</div>
          {nos.map((n) => (
            <NodeRow key={n.nodeId} node={n} />
          ))}
        </div>
      ))}
    </div>
  );
}
