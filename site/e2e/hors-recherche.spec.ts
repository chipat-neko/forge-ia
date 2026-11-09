// Les textes bruts des démos n'entrent pas dans l'index de la recherche
// (revue finale, m8) : les prénoms tirés au hasard de l'ouverture de 0.5, le
// tableau avant/après de l'avant-goût, la grille de l'atelier des formes, le
// dessin du neurone, et les jetons numérotés de l'atelier de 1.3. Les dates de
// relevé de l'annuaire des données non plus. Chacun porte
// data-pagefind-ignore, ou se trouve dans un élément qui le porte, comme les
// textes de l'atelier de 0.1 depuis le plan 4.
//
// Les pages des brouillons se construisent avec FORGE_ESSAIS=1, comme pour les
// autres parcours : elles sont visitées à leur adresse définitive.
import { test, expect } from '@playwright/test';

/** [adresse, sélecteur, ce que c'est]. */
const ZONES: [string, string, string][] = [
  ['/forge-ia/partie-0/0-1/', '[data-test="ms-suite"]', 'la suite de mots de l’atelier de 0.1'],
  ['/forge-ia/partie-0/0-4/', '[data-test="formes-grille"]', 'la grille de l’atelier des formes'],
  ['/forge-ia/partie-0/0-5/', '[data-test="ouverture-prenom"]', 'les prénoms de l’ouverture de 0.5'],
  ['/forge-ia/partie-0/0-5/', '[data-test="neu-dessin"]', 'le dessin du neurone'],
  ['/forge-ia/partie-0/0-5/', '[data-test="mini-avant-apres"]', 'le tableau avant/après de l’avant-goût'],
  ['/forge-ia/partie-1/1-3/', '[data-test="jetons"]', 'les jetons numérotés de l’atelier de 1.3'],
  // L'annuaire entre dans l'index, mais pas ses colonnes de dates (tâche 9 du plan 5).
  ['/forge-ia/annexes/annuaire/', '[data-test="releve-le"]', 'les dates de relevé de l’annuaire'],
];

test('les textes bruts des démos restent hors de l’index de la recherche', async ({ page }) => {
  for (const [adresse, selecteur, quoi] of ZONES) {
    expect((await page.goto(adresse))?.status(), adresse).toBe(200);
    const zone = page.locator(selecteur).first();
    await expect(zone, quoi).toBeAttached();
    expect(await zone.evaluate((e) => e.closest('[data-pagefind-ignore]') !== null), quoi).toBe(true);
  }
});
