// La longueur des lignes de prose sur une tablette (point mis de côté à la
// tâche 7) : entre 600 et 899 px de fenêtre, la colonne de lecture ne doit pas
// dépasser 80 caractères par ligne, comme sur ordinateur et sur téléphone
// (plusLongueLigne). Le parcours visite à 720 px tous les chapitres, parus et
// brouillons (construits avec FORGE_ESSAIS=1), d'après les fichiers sur le
// disque : un git mv de parution ne l'oblige pas à changer.
import { existsSync, readdirSync } from 'node:fs';
import { test, expect } from '@playwright/test';
import { plusLongueLigne } from './outils';

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

const CHAPITRES = [...adresses('src/content/chapitres'), ...adresses('src/brouillons/chapitres')];

test('à 720 px, aucune ligne de prose ne dépasse 80 caractères', async ({ page }, info) => {
  // Une seule largeur, réglée ici : le projet mobile referait la même chose.
  test.skip(info.project.name !== 'ordinateur', 'la largeur est réglée par le parcours');
  test.setTimeout(180_000);
  expect(CHAPITRES.length).toBeGreaterThan(0);
  await page.setViewportSize({ width: 720, height: 900 });
  const trop: string[] = [];
  for (const adresse of CHAPITRES) {
    await page.goto(adresse);
    await page.evaluate(() => document.fonts.ready.then(() => undefined));
    const { longueur, ligne } = await plusLongueLigne(page);
    if (longueur > 80) trop.push(`${adresse} : ${longueur} caractères, « ${ligne} »`);
  }
  expect(trop).toEqual([]);
});
