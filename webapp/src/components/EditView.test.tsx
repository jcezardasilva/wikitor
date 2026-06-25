import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../api';
import { EditView } from './EditView';

// O editor visual (Milkdown/Crepe) usa ProseMirror/DOM real, instável em jsdom.
// Stub leve que expõe o contrato value/onChange para testar a integração no EditView.
vi.mock('./WysiwygEditor', () => ({
  WysiwygEditor: ({ value, onChange }: { value: string; onChange: (md: string) => void }) => (
    <textarea
      data-testid="wysiwyg"
      value={value}
      onChange={(e) => onChange(e.target.value)}
    />
  ),
}));

afterEach(() => {
  vi.restoreAllMocks();
  localStorage.clear();
});

describe('EditView', () => {
  it('exige título e assunto antes de salvar', async () => {
    const saveSpy = vi.spyOn(api, 'saveDocument');
    const onSaved = vi.fn();
    render(<EditView seed={null} onSaved={onSaved} />);

    await userEvent.click(screen.getByText('Salvar'));

    expect(screen.getByText('Título e assunto são obrigatórios.')).toBeInTheDocument();
    expect(saveSpy).not.toHaveBeenCalled();
    expect(onSaved).not.toHaveBeenCalled();
  });

  it('salva e propaga o documento criado', async () => {
    const doc = {
      id: 'redes/osi',
      titulo: 'OSI',
      assunto: 'redes',
      nivel: 'iniciante' as const,
      resumo: '',
      status: 'publicado',
      referencias: [],
      atualizado_em: '2026-06-20',
      conteudo: '# OSI',
    };
    vi.spyOn(api, 'saveDocument').mockResolvedValue(doc);
    const onSaved = vi.fn();
    render(<EditView seed={null} onSaved={onSaved} />);

    await userEvent.type(screen.getByPlaceholderText('Título do documento'), 'OSI');
    await userEvent.type(screen.getByLabelText('assunto:'), 'redes');
    await userEvent.click(screen.getByText('Salvar'));

    expect(api.saveDocument).toHaveBeenCalledWith(
      expect.objectContaining({ titulo: 'OSI', assunto: 'redes', nivel: 'iniciante' }),
    );
    expect(onSaved).toHaveBeenCalledWith(doc);
  });

  it('abre no editor markdown por padrão (sem preferência salva)', () => {
    render(<EditView seed={null} onSaved={vi.fn()} />);
    expect(screen.getByPlaceholderText(/Escreva o conteúdo em markdown/)).toBeInTheDocument();
    expect(screen.queryByTestId('wysiwyg')).not.toBeInTheDocument();
  });

  it('alterna para Visual e lembra a escolha em localStorage', async () => {
    const { unmount } = render(<EditView seed={null} onSaved={vi.fn()} />);

    await userEvent.click(screen.getByRole('button', { name: 'Visual' }));
    expect(await screen.findByTestId('wysiwyg')).toBeInTheDocument();
    expect(localStorage.getItem('wikitor.editorKind')).toBe('wysiwyg');

    // Remontar: deve abrir já em Visual lendo a preferência.
    unmount();
    render(<EditView seed={null} onSaved={vi.fn()} />);
    expect(await screen.findByTestId('wysiwyg')).toBeInTheDocument();
  });

  it('mantém o conteúdo ao alternar de modo (fonte única) e salva o markdown', async () => {
    vi.spyOn(api, 'saveDocument').mockResolvedValue({
      id: 'redes/x', titulo: 'X', assunto: 'redes', nivel: 'iniciante', resumo: '',
      status: 'publicado', referencias: [], atualizado_em: '2026-06-20', conteudo: '',
    });
    render(<EditView seed={null} onSaved={vi.fn()} />);

    await userEvent.type(screen.getByPlaceholderText('Título do documento'), 'X');
    await userEvent.type(screen.getByLabelText('assunto:'), 'redes');

    // Escreve no modo Visual…
    await userEvent.click(screen.getByRole('button', { name: 'Visual' }));
    const wysiwyg = await screen.findByTestId('wysiwyg');
    await userEvent.type(wysiwyg, '# Olá');

    // …alterna para Markdown: conteúdo preservado no textarea.
    await userEvent.click(screen.getByRole('button', { name: 'Markdown' }));
    const textarea = screen.getByPlaceholderText(/Escreva o conteúdo em markdown/);
    expect(textarea).toHaveValue('# Olá');

    await userEvent.click(screen.getByText('Salvar'));
    expect(api.saveDocument).toHaveBeenCalledWith(
      expect.objectContaining({ conteudo: '# Olá' }),
    );
  });
});
