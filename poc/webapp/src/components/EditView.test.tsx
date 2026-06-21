import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../api';
import { EditView } from './EditView';

afterEach(() => vi.restoreAllMocks());

describe('EditView', () => {
  it('exige título e assunto antes de salvar', async () => {
    const saveSpy = vi.spyOn(api, 'saveDocument');
    const onSaved = vi.fn();
    render(<EditView seed={null} onSaved={onSaved} />);

    await userEvent.click(screen.getByText('Salvar (gera resumo + reindexa)'));

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

    await userEvent.type(screen.getByLabelText('Título'), 'OSI');
    await userEvent.type(screen.getByLabelText('Assunto'), 'redes');
    await userEvent.click(screen.getByText('Salvar (gera resumo + reindexa)'));

    expect(api.saveDocument).toHaveBeenCalledWith(
      expect.objectContaining({ titulo: 'OSI', assunto: 'redes', nivel: 'iniciante' }),
    );
    expect(onSaved).toHaveBeenCalledWith(doc);
  });
});
