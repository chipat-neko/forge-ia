// Parcours des brouillons de chapitres : src/brouillons/chapitres/<p>-<n>.mdx.
// Un brouillon n'est construit qu'avec FORGE_ESSAIS=1 (la construction de
// Playwright), à son adresse définitive, hors de l'index de la recherche ; les
// pages de partie, le pied des chapitres et l'accueil ne lisent que les
// chapitres parus, et le montrent donc « à venir ».
//
// Les tests suivent les brouillons présents sur le disque : à sa parution (le
// git mv vers src/content/chapitres/), un chapitre quitte ces tests sans les
// retoucher. Sans aucun brouillon, ils sont sautés.
import { existsSync, readdirSync } from 'node:fs';
import { test, expect } from '@playwright/test';
import { trouverChapitre } from '../src/lib/parcours';

// Playwright tourne dans site/.
const DOSSIER = 'src/brouillons/chapitres';
const BROUILLONS = existsSync(DOSSIER)
  ? readdirSync(DOSSIER)
      .filter((f) => f.endsWith('.mdx'))
      .map((f) => {
        const nom = f.replace(/\.mdx$/, '');
        const [p, n] = nom.split('-');
        return { numero: `${p}.${n}`, partie: p, adresse: `/forge-ia/partie-${p}/${nom}/` };
      })
  : [];

test('un brouillon se lit à son adresse, hors de la recherche', async ({ page }) => {
  test.skip(BROUILLONS.length === 0, 'aucun brouillon');
  for (const { numero, partie, adresse } of BROUILLONS) {
    expect((await page.goto(adresse))?.status(), adresse).toBe(200);
    const { total } = trouverChapitre(numero);
    await expect(page.locator('header')).toContainText(`Partie ${partie}, chapitre ${numero} sur ${total}`);
    await expect(page.locator('[data-pagefind-body]')).toHaveCount(0);
  }
});

test('la page de sa partie le montre encore « à venir »', async ({ page }) => {
  test.skip(BROUILLONS.length === 0, 'aucun brouillon');
  for (const { numero, partie } of BROUILLONS) {
    await page.goto(`/forge-ia/partie-${partie}/`);
    await expect(page.locator(`[data-chapitre-carte="${numero}"]`)).toHaveAttribute('data-etat', 'a-venir');
  }
});
