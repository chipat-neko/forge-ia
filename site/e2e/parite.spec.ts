// Parcours de la parité, sur les pages d'essai /forge-ia/essais/parite/ et
// /forge-ia/essais/parite-partie-0/ (construites seulement avec FORGE_ESSAIS=1,
// voir src/essais/parite.mdx et parite-partie-0.mdx).
//
// La première refait dans le navigateur les quatre fichiers d'attendus du
// mini-modèle (ControleParite.svelte, avec src/lib/mini-modele/parite.ts) ; la
// seconde, ceux des jumeaux de la Partie 0 (jeu="partie-0", avec
// src/lib/partie-0/parite.ts). Chacune les écrit en JSON. Ce parcours les
// compare aux fichiers eux-mêmes : mêmes clés, ni plus ni moins, et mêmes
// valeurs (pour le mini-modèle, des motifs hexadécimaux, au bit près). Il
// tourne dans les projets Chrome (ordinateur, mobile) et, avec
// FORGE_TOUS_NAVIGATEURS=1, dans Firefox et WebKit (projets parite-firefox et
// parite-webkit, voir playwright.config.ts) : c'est la seule façon de voir
// qu'un moteur JavaScript s'écarte du Python.
import { readdirSync, readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import { cheminsDesCles } from '../src/lib/mini-modele/cles-json';
import { verifierAxe, verifierSansDebordement, verifierTypographie } from './outils';

const PAGE = '/forge-ia/essais/parite/';
const NOMS = ['calcul', 'donnees', 'modele', 'attention'] as const;

// La page de la Partie 0 : chaque calcul de src/lib/partie-0/parite.ts (CALCULS_PARTIE_0),
// et le fichier d'attendus du Python qu'il refait (chemin depuis site/).
const PAGE_PARTIE_0 = '/forge-ia/essais/parite-partie-0/';
const FICHIERS_PARTIE_0: Readonly<Record<string, string>> = {
  'mot-suivant': '../projets/0.1-python/tests/attendus.json',
};

// calculer() attend jusqu'à 60 s la fin du calcul (Firefox et WebKit sont plus lents que Chrome) :
// le délai par défaut de Playwright, 30 s, couperait le test avant ce délai d'attente.
test.describe.configure({ timeout: 90_000 });

/** Un fichier d'attendus écrit par le Python (Playwright tourne dans site/). */
function lireAttendus(nom: string): unknown {
  return JSON.parse(readFileSync(`../projets/mini-modele/tests/attendus-${nom}.json`, 'utf8'));
}

const racine = (p: Page) => p.locator('[data-test="parite"]');
const etat = (p: Page) => p.locator('[data-test="parite-etat"]');
const resultat = (p: Page, nom: string) => p.locator(`[data-test="parite-${nom}"]`);

/** Ouvre la page et attend la fin du calcul ; échoue avec la ligne d'état si un calcul a échoué. */
async function calculer(page: Page, adresse = PAGE): Promise<void> {
  await page.goto(adresse);
  await expect(racine(page)).toHaveAttribute('data-pret', /^(oui|erreur)$/, { timeout: 60_000 });
  expect(await racine(page).getAttribute('data-pret'), await etat(page).innerText()).toBe('oui');
}

/** La durée du calcul va dans le rapport, et c'est bien le moteur de ce projet qui a calculé, dans la page. */
async function verifierMoteur(page: Page, browserName: string): Promise<void> {
  // La durée du calcul dans ce moteur, lue dans la ligne d'état : elle apparaît dans le rapport.
  test.info().annotations.push({ type: 'calcul', description: `${browserName} : ${await etat(page).innerText()}` });
  const moteur = (await racine(page).getAttribute('data-moteur')) ?? '';
  if (browserName === 'chromium') expect(moteur).toMatch(/Chrome\//);
  if (browserName === 'firefox') expect(moteur).toMatch(/Firefox\//);
  if (browserName === 'webkit') {
    expect(moteur).toMatch(/AppleWebKit\//);
    expect(moteur).not.toMatch(/Chrome\/|Firefox\//);
  }
}

test('le navigateur refait tous les attendus du Python, au bit près', async ({ page, browserName }) => {
  // Chaque fichier d'attendus du Python est comparé : aucun ne doit échapper à la liste NOMS.
  const fichiers = readdirSync('../projets/mini-modele/tests').flatMap((f) => /^attendus-(.+)\.json$/.exec(f)?.[1] ?? []);
  expect(fichiers.sort(), 'fichiers projets/mini-modele/tests/attendus-*.json').toEqual([...NOMS].sort());
  await calculer(page);
  await verifierMoteur(page, browserName);
  for (const nom of NOMS) {
    const attendu = lireAttendus(nom);
    const calcule = JSON.parse((await resultat(page, nom).textContent()) ?? '');
    // Les clés d'abord (le message dit laquelle manque ou est en trop), puis tout le contenu.
    expect.soft(cheminsDesCles(calcule), `clés de attendus-${nom}.json (${browserName})`).toEqual(cheminsDesCles(attendu));
    expect.soft(calcule, `attendus-${nom}.json (${browserName})`).toStrictEqual(attendu);
  }
});

test('Partie 0 : le navigateur refait les attendus des jumeaux du Python, à l’identique', async ({
  page,
  browserName,
}) => {
  await calculer(page, PAGE_PARTIE_0);
  await verifierMoteur(page, browserName);
  // Chaque calcul de la page est comparé à son fichier : aucun ne doit échapper à FICHIERS_PARTIE_0.
  const calcules = await page.locator('[data-test="parite"] pre').evaluateAll((pres) =>
    pres.map((pre) => pre.getAttribute('data-test')),
  );
  const noms = Object.keys(FICHIERS_PARTIE_0);
  expect(calcules, 'calculs de la page parite-partie-0').toEqual(noms.map((nom) => `parite-${nom}`));
  // La ligne d'état compte les fichiers refaits (un seul : au singulier).
  await expect(etat(page)).toContainText(
    noms.length === 1 ? 'le fichier d’attendus est refait' : 'fichiers d’attendus sont refaits',
  );
  for (const [nom, chemin] of Object.entries(FICHIERS_PARTIE_0)) {
    const attendu: unknown = JSON.parse(readFileSync(chemin, 'utf8'));
    const calcule: unknown = JSON.parse((await resultat(page, nom).textContent()) ?? '');
    // Les clés d'abord (le message dit laquelle manque ou est en trop), puis tout le contenu.
    expect.soft(cheminsDesCles(calcule), `clés de ${chemin} (${browserName})`).toEqual(cheminsDesCles(attendu));
    expect.soft(calcule, `${chemin} (${browserName})`).toStrictEqual(attendu);
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
