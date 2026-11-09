// Parcours de la parité, sur les pages d'essai /forge-ia/essais/parite/,
// /forge-ia/essais/parite-partie-0/ et /forge-ia/essais/parite-partie-1/
// (construites seulement avec FORGE_ESSAIS=1, voir src/essais/parite.mdx,
// parite-partie-0.mdx et parite-partie-1.mdx).
//
// La première refait dans le navigateur les quatre fichiers d'attendus du
// mini-modèle (ControleParite.svelte, avec src/lib/mini-modele/parite.ts) ; la
// seconde, ceux des jumeaux de la Partie 0 (jeu="partie-0", avec
// src/lib/partie-0/parite.ts) : le mot suivant de 0.1, puis les vecteurs, les
// matrices, la descente et les tirages de 0.2. Chacune les écrit en JSON. Ce
// parcours les compare aux fichiers eux-mêmes : mêmes clés, ni plus ni moins, et
// mêmes valeurs (pour le mini-modèle, des motifs hexadécimaux ; pour la Partie 0,
// des flottants), au bit près. Les sections que le site lit sans les refaire
// (SECTIONS_NON_REFAITES, src/lib/partie-0/fichiers.ts : softmax et −ln p de 0.2,
// qui passent par exp et log, et ce qui ne sert qu'en Python) sont retirées du
// fichier avant la comparaison. La troisième refait ceux des jumeaux de la
// Partie 1 (jeu="partie-1", avec src/lib/partie-1/parite.ts) : le modèle à
// n-grammes de 1.1, sans ses perplexités (CLES_NON_REFAITES,
// src/lib/partie-1/fichiers.ts), puis le nettoyage des textes de 1.2 (blancs de Python,
// texte nettoyé, empreinte SHA-1 par crypto.subtle, verdicts du tri). Il tourne dans les projets Chrome (ordinateur,
// mobile) et, avec FORGE_TOUS_NAVIGATEURS=1, dans Firefox et WebKit (projets
// parite-firefox et parite-webkit, voir playwright.config.ts) : c'est la seule
// façon de voir qu'un moteur JavaScript s'écarte du Python.
import { readdirSync, readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import { cheminsDesCles } from '../src/lib/mini-modele/cles-json';
import { FICHIERS_PARTIE_0, partieRefaite } from '../src/lib/partie-0/fichiers';
import { FICHIERS_PARTIE_1, partieRefaite as partieRefaite1 } from '../src/lib/partie-1/fichiers';
import { verifierAxe, verifierSansDebordement, verifierTypographie } from './outils';

const PAGE = '/forge-ia/essais/parite/';
const NOMS = ['calcul', 'donnees', 'modele', 'attention'] as const;
const PAGE_PARTIE_0 = '/forge-ia/essais/parite-partie-0/';
const PAGE_PARTIE_1 = '/forge-ia/essais/parite-partie-1/';

/**
 * Une page de parité : son adresse, chaque calcul avec le fichier du Python qu'il
 * refait (chemin depuis site/), et ce que la page doit en retrouver (tout le
 * fichier, ou le fichier sans ses sections non refaites).
 */
interface PageDeParite {
  adresse: string;
  fichiers: [nom: string, chemin: string][];
  aRetrouver: (nom: string, fichier: Record<string, unknown>) => Record<string, unknown>;
}

const PAGES: PageDeParite[] = [
  {
    adresse: PAGE,
    fichiers: NOMS.map((nom) => [nom, `../projets/mini-modele/tests/attendus-${nom}.json`]),
    aRetrouver: (_nom, fichier) => fichier,
  },
  {
    adresse: PAGE_PARTIE_0,
    // FICHIERS_PARTIE_0 donne les chemins depuis la racine du dépôt (src/lib/partie-0/fichiers.ts).
    fichiers: Object.entries(FICHIERS_PARTIE_0).map(([nom, chemin]) => [nom, `../${chemin}`]),
    aRetrouver: partieRefaite,
  },
  {
    adresse: PAGE_PARTIE_1,
    // FICHIERS_PARTIE_1 donne les chemins depuis la racine du dépôt (src/lib/partie-1/fichiers.ts).
    fichiers: Object.entries(FICHIERS_PARTIE_1).map(([nom, chemin]) => [nom, `../${chemin}`]),
    aRetrouver: partieRefaite1,
  },
];

// calculer() attend jusqu'à 60 s la fin du calcul (Firefox et WebKit sont plus lents que Chrome) :
// le délai par défaut de Playwright, 30 s, couperait le test avant ce délai d'attente.
test.describe.configure({ timeout: 90_000 });

const racine = (p: Page) => p.locator('[data-test="parite"]');
const etat = (p: Page) => p.locator('[data-test="parite-etat"]');
const resultat = (p: Page, nom: string) => p.locator(`[data-test="parite-${nom}"]`);

/** Ouvre la page et attend la fin du calcul ; échoue avec la ligne d'état si un calcul a échoué. */
async function calculer(page: Page, adresse: string): Promise<void> {
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

/**
 * Compare ce que la page a écrit à chaque fichier du Python : la page ne refait
 * rien d'autre, puis, fichier par fichier, les clés d'abord (le message dit
 * laquelle manque ou est en trop), puis tout le contenu.
 */
async function comparerAuxFichiers(
  page: Page,
  browserName: string,
  { fichiers, aRetrouver }: PageDeParite,
): Promise<void> {
  const calcules = await page.locator('[data-test="parite"] pre').evaluateAll((pres) =>
    pres.map((pre) => pre.getAttribute('data-test')),
  );
  expect(calcules, `calculs de la page (${browserName})`).toEqual(fichiers.map(([nom]) => `parite-${nom}`));
  for (const [nom, chemin] of fichiers) {
    const attendu: unknown = aRetrouver(nom, JSON.parse(readFileSync(chemin, 'utf8')) as Record<string, unknown>);
    const calcule: unknown = JSON.parse((await resultat(page, nom).textContent()) ?? '');
    expect.soft(cheminsDesCles(calcule), `clés de ${chemin} (${browserName})`).toEqual(cheminsDesCles(attendu));
    expect.soft(calcule, `${chemin} (${browserName})`).toStrictEqual(attendu);
  }
}

test('le navigateur refait tous les attendus du Python, au bit près', async ({ page, browserName }) => {
  // Chaque fichier d'attendus du Python est comparé : aucun ne doit échapper à la liste NOMS.
  const fichiers = readdirSync('../projets/mini-modele/tests').flatMap((f) => /^attendus-(.+)\.json$/.exec(f)?.[1] ?? []);
  expect(fichiers.sort(), 'fichiers projets/mini-modele/tests/attendus-*.json').toEqual([...NOMS].sort());
  await calculer(page, PAGE);
  await verifierMoteur(page, browserName);
  await comparerAuxFichiers(page, browserName, PAGES[0]);
});

test('Partie 0 : le navigateur refait les attendus des jumeaux du Python, à l’identique', async ({
  page,
  browserName,
}) => {
  await calculer(page, PAGE_PARTIE_0);
  await verifierMoteur(page, browserName);
  // La ligne d'état compte les fichiers refaits (un seul : au singulier).
  await expect(etat(page)).toContainText(
    PAGES[1].fichiers.length === 1 ? 'le fichier d’attendus est refait' : 'fichiers d’attendus sont refaits',
  );
  // Le fichier de 0.2 est bien dans la liste, à côté de celui de 0.1.
  expect(PAGES[1].fichiers.map(([nom]) => nom)).toEqual(['mot-suivant', 'maths']);
  await comparerAuxFichiers(page, browserName, PAGES[1]);
});

test('Partie 1 : le navigateur refait les attendus des jumeaux du Python, à l’identique', async ({
  page,
  browserName,
}) => {
  await calculer(page, PAGE_PARTIE_1);
  await verifierMoteur(page, browserName);
  await expect(etat(page)).toContainText(
    PAGES[2].fichiers.length === 1 ? 'le fichier d’attendus est refait' : 'fichiers d’attendus sont refaits',
  );
  // Les fichiers de 1.1 (n-grammes) et de 1.2 (nettoyage, dont l'empreinte est asynchrone) sont bien dans la liste.
  expect(PAGES[2].fichiers.map(([nom]) => nom)).toEqual(['ngrammes', 'nettoyeur']);
  await comparerAuxFichiers(page, browserName, PAGES[2]);
});

for (const { adresse, fichiers } of PAGES) {
  test(`sans JavaScript, rien n’est calculé : pas de résultat venu de la construction (${adresse})`, async ({
    browser,
    baseURL,
  }) => {
    // Le HTML construit par Astro (dans Node) ne doit rien contenir de calculé : sinon, les parcours
    // ci-dessus compareraient les calculs de Node, et non ceux du navigateur.
    const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
    const page = await ctx.newPage();
    await page.goto(adresse);
    await expect(racine(page)).toHaveCount(1);
    expect(await racine(page).getAttribute('data-pret')).toBeNull();
    expect(await racine(page).getAttribute('data-moteur')).toBeNull();
    for (const [nom] of fichiers) {
      await expect(resultat(page, nom)).toHaveCount(1);
      expect(await resultat(page, nom).textContent(), nom).toBe('');
    }
    await expect(etat(page)).toContainText('sans JavaScript, rien n’est calculé');
    await ctx.close();
  });

  test(`accessibilité, largeur et typographie, résultats ouverts (${adresse})`, async ({ page }) => {
    await calculer(page, adresse);
    // Tous les JSON dépliés : ils reviennent à la ligne, sans faire déborder la page.
    for (const resume of await page.locator('[data-test="parite"] summary').all()) await resume.click();
    for (const [nom] of fichiers) await expect(resultat(page, nom)).toBeVisible();
    await verifierSansDebordement(page);
    await verifierTypographie(etat(page));
    await verifierAxe(page);
  });
}
