// Parcours de la parité, sur la page d'essai /forge-ia/essais/parite/
// (construite seulement avec FORGE_ESSAIS=1, voir src/essais/parite.mdx).
//
// La page refait dans le navigateur les quatre fichiers d'attendus du Python
// (ControleParite.svelte, avec src/lib/mini-modele/parite.ts) et les écrit en
// JSON. Ce parcours les compare aux fichiers eux-mêmes : mêmes clés, ni plus
// ni moins, et mêmes motifs hexadécimaux, au bit près. Il tourne dans les
// projets Chrome (ordinateur, mobile) et, avec FORGE_TOUS_NAVIGATEURS=1, dans
// Firefox et WebKit (projets parite-firefox et parite-webkit, voir
// playwright.config.ts) : c'est la seule façon de voir qu'un moteur
// JavaScript s'écarte du Python.
import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import { cheminsDesCles } from '../src/lib/mini-modele/cles-json';
import { verifierAxe, verifierSansDebordement, verifierTypographie } from './outils';

const PAGE = '/forge-ia/essais/parite/';
const NOMS = ['calcul', 'donnees', 'modele', 'attention'] as const;

/** Un fichier d'attendus écrit par le Python (Playwright tourne dans site/). */
function lireAttendus(nom: string): unknown {
  return JSON.parse(readFileSync(`../projets/mini-modele/tests/attendus-${nom}.json`, 'utf8'));
}

const racine = (p: Page) => p.locator('[data-test="parite"]');
const etat = (p: Page) => p.locator('[data-test="parite-etat"]');
const resultat = (p: Page, nom: string) => p.locator(`[data-test="parite-${nom}"]`);

/** Ouvre la page et attend la fin du calcul ; échoue avec la ligne d'état si un calcul a échoué. */
async function calculer(page: Page): Promise<void> {
  await page.goto(PAGE);
  await expect(racine(page)).toHaveAttribute('data-pret', /^(oui|erreur)$/, { timeout: 60_000 });
  expect(await racine(page).getAttribute('data-pret'), await etat(page).innerText()).toBe('oui');
}

test('le navigateur refait tous les attendus du Python, au bit près', async ({ page, browserName }) => {
  await calculer(page);
  // La durée du calcul dans ce moteur, lue dans la ligne d'état : elle apparaît dans le rapport.
  test.info().annotations.push({ type: 'calcul', description: `${browserName} : ${await etat(page).innerText()}` });
  // C'est bien le moteur de ce projet qui a calculé, dans la page.
  const moteur = (await racine(page).getAttribute('data-moteur')) ?? '';
  if (browserName === 'chromium') expect(moteur).toMatch(/Chrome\//);
  if (browserName === 'firefox') expect(moteur).toMatch(/Firefox\//);
  if (browserName === 'webkit') {
    expect(moteur).toMatch(/AppleWebKit\//);
    expect(moteur).not.toMatch(/Chrome\/|Firefox\//);
  }
  for (const nom of NOMS) {
    const attendu = lireAttendus(nom);
    const calcule = JSON.parse((await resultat(page, nom).textContent()) ?? '');
    // Les clés d'abord (le message dit laquelle manque ou est en trop), puis tout le contenu.
    expect.soft(cheminsDesCles(calcule), `clés de attendus-${nom}.json (${browserName})`).toEqual(cheminsDesCles(attendu));
    expect.soft(calcule, `attendus-${nom}.json (${browserName})`).toStrictEqual(attendu);
  }
});

test('sans JavaScript, rien n’est calculé : pas de résultat venu de la construction', async ({ browser, baseURL }) => {
  // Le HTML construit par Astro (dans Node) ne doit rien contenir de calculé : sinon, le parcours
  // ci-dessus comparerait les calculs de Node, et non ceux du navigateur.
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  await expect(racine(page)).toHaveCount(1);
  expect(await racine(page).getAttribute('data-pret')).toBeNull();
  expect(await racine(page).getAttribute('data-moteur')).toBeNull();
  for (const nom of NOMS) {
    await expect(resultat(page, nom)).toHaveCount(1);
    expect(await resultat(page, nom).textContent(), nom).toBe('');
  }
  await expect(etat(page)).toContainText('sans JavaScript, rien n’est calculé');
  await ctx.close();
});

test('accessibilité, largeur et typographie, résultats ouverts', async ({ page }) => {
  await calculer(page);
  // Les quatre JSON dépliés : ils reviennent à la ligne, sans faire déborder la page.
  for (const resume of await page.locator('[data-test="parite"] summary').all()) await resume.click();
  for (const nom of NOMS) await expect(resultat(page, nom)).toBeVisible();
  await verifierSansDebordement(page);
  await verifierTypographie(etat(page));
  await verifierAxe(page);
});
