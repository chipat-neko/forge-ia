// Parcours de la parution : ce qui peut paraître et ce qui ne le peut pas.
//
// - Un chapitre paru (src/content/chapitres/<p>-<n>.mdx) n'a plus aucune valeur
//   « à mesurer » ([data-a-mesurer], posé par SortieCommande et TableauChronos
//   quand une mesure manque) : c'est une des conditions de parution du README.
// - Chaque brouillon (src/brouillons/chapitres/<p>-<n>.mdx) se construit, avec
//   FORGE_ESSAIS=1, à son adresse définitive.
//
// Les deux tests suivent les fichiers présents sur le disque : le git mv d'une
// parution ne les oblige pas à changer. Sans aucun brouillon, le second est sauté.
import { existsSync, readdirSync } from 'node:fs';
import { test, expect } from '@playwright/test';

/** Les adresses des chapitres d'un dossier de MDX (Playwright tourne dans site/). */
function adresses(dossier: string): string[] {
  if (!existsSync(dossier)) return [];
  return readdirSync(dossier)
    .filter((f) => f.endsWith('.mdx'))
    .map((f) => {
      const nom = f.replace(/\.mdx$/, '');
      return `/forge-ia/partie-${nom.split('-')[0]}/${nom}/`;
    });
}

const PARUS = adresses('src/content/chapitres');
const BROUILLONS = adresses('src/brouillons/chapitres');

test('un chapitre paru n’a plus aucune valeur « à mesurer »', async ({ page }) => {
  expect(PARUS.length, 'aucun chapitre paru trouvé dans src/content/chapitres').toBeGreaterThan(0);
  for (const adresse of PARUS) {
    expect((await page.goto(adresse))?.status(), adresse).toBe(200);
    await expect(page.locator('[data-a-mesurer]'), adresse).toHaveCount(0);
  }
});

test('chaque brouillon se construit à son adresse', async ({ page }) => {
  test.skip(BROUILLONS.length === 0, 'aucun brouillon');
  for (const adresse of BROUILLONS) {
    expect((await page.goto(adresse))?.status(), adresse).toBe(200);
    await expect(page.locator('article.chapitre'), adresse).toHaveCount(1);
  }
});
