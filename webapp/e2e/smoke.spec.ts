import { expect, test } from '@playwright/test';

// Golden path com o backend mockado: índice -> abrir doc -> alternar abas.
test.beforeEach(async ({ page }) => {
  await page.route('**/api/index', (route) =>
    route.fulfill({
      json: { assuntos: [{ assunto: 'redes', resumo: '', path: '', total_docs: 1 }] },
    }),
  );
  await page.route('**/api/subjects/redes', (route) =>
    route.fulfill({
      json: {
        assunto: 'redes',
        resumo: '',
        relacionados: [],
        niveis: {
          iniciante: [
            { id: 'redes/osi', path: '', titulo: 'Modelo OSI', resumo: 'As 7 camadas', nivel: 'iniciante' },
          ],
        },
      },
    }),
  );
  await page.route('**/api/docs/redes/osi', (route) =>
    route.fulfill({
      json: {
        id: 'redes/osi',
        titulo: 'Modelo OSI',
        assunto: 'redes',
        nivel: 'iniciante',
        resumo: 'As 7 camadas',
        status: 'publicado',
        referencias: [],
        atualizado_em: '2026-06-20',
        conteudo: '# Modelo OSI\n\nAs **7 camadas** de rede.',
      },
    }),
  );
});

test('navega no índice e abre um documento', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /Wikitor/ })).toBeVisible();

  await page.getByRole('button', { name: 'Modelo OSI' }).click();

  await expect(page.getByRole('heading', { name: 'Modelo OSI' })).toBeVisible();
  await expect(page.getByText('As 7 camadas de rede.')).toBeVisible();
});

test('alterna entre as abas', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Editar' }).click();
  await expect(page.getByRole('heading', { name: 'Edição manual' })).toBeVisible();

  await page.getByRole('button', { name: 'Assistente IA' }).click();
  await expect(page.getByPlaceholder(/Pergunte algo/)).toBeVisible();
});
