// Parcours du chapitre 1.1, « Ce qu'est vraiment un modèle de langage » : un
// brouillon (src/brouillons/chapitres/1-1.mdx) tant qu'il n'a pas paru,
// construit à son adresse définitive avec FORGE_ESSAIS=1.
//
// Les attendus viennent du jumeau du modèle à n-grammes
// (src/lib/partie-1/ngrammes.ts) et des paris (paris-1-1.ts), appliqués au
// texte du projet et aux perplexités du Python, lus sur le disque : un
// parcours, chargé par Node sans Vite, n'importe ni ?raw, ni .json, ni astro:*
// (P8). Il ne passe donc pas par texte-1-1.ts.
import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import type { Choix } from '../src/lib/choix';
import { nombre } from '../src/lib/nombres';
import { trouverChapitre } from '../src/lib/parcours';
import { alphabet, compterParOrdre, couper, generer, tirage } from '../src/lib/partie-1/ngrammes';
import {
  BARRES_MONTREES,
  choixContexte,
  choixPerplexite,
  choixSuivant,
  choixTemperature,
  CONTEXTE_INITIAL,
  etatDeLAtelier,
  GRAINE_INITIALE,
  LONGUEUR_SUITE,
  messageBoucle,
  messageCourt,
  messageRecul,
  minimumDesPerplexites,
  N_INITIAL,
  N_MAX,
  ouvertureDuChapitre,
  TEMPERATURE_INITIALE,
  TEMPERATURES_ATELIER,
} from '../src/lib/partie-1/paris-1-1';
import { extraireRegion } from '../src/lib/regions';
import { typographier } from '../src/lib/typo';
import {
  attendreHydratation,
  plusLongueLigne,
  verifierAxe,
  verifierLiensVersParus,
  verifierSansDebordement,
  verifierTypographieHorsCode,
  verifierVoisin,
} from './outils';

const PAGE = '/forge-ia/partie-1/1-1/';
const FINE = '\u202F';

// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
const PROJET = '../projets/1.1-modele-de-langage';
const TEXTE = readFileSync(`${PROJET}/donnees/texte-du-site.txt`, 'utf8');
const ATTENDUS = JSON.parse(readFileSync(`${PROJET}/tests/attendus.json`, 'utf8')) as {
  ordres: { n: number; perplexite_entrainement: number; perplexite_validation: number }[];
};
const PERPLEXITES = ATTENDUS.ordres.map((o) => ({
  n: o.n,
  entrainement: o.perplexite_entrainement,
  validation: o.perplexite_validation,
}));
const LETTRES = alphabet(TEXTE);
const COMPTES = compterParOrdre(couper(TEXTE)[0], N_MAX);

// Ce qui n'est pas du texte du chapitre mais des données brutes : le champ de
// l'atelier, la suite écrite par le modèle (le texte du site garde ses
// apostrophes droites) et les caractères des barres et de l'ouverture.
const BRUT = 'input, [data-test="ml-suite"], [data-caractere]';

/** Le texte exact d'un élément (textContent : toHaveText ramènerait U+202F à une espace ordinaire). */
async function texteExact(page: Page, selecteur: string): Promise<string> {
  return (await page.locator(selecteur).textContent()) ?? '';
}

/** Attend la fin des animations en cours (fondu du verrou, verdict des paris) : axe mesure alors les vraies couleurs. */
async function attendreAnimations(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)).then(() => undefined));
}

/** Le texte d'un choix tel qu'un bouton l'affiche : le code tel quel, le reste typographié. */
function affiche(choix: Choix): string {
  return choix.texte
    .split('`')
    .map((morceau, i) => (i % 2 === 1 ? morceau : typographier(morceau)))
    .join('');
}

/** Ouvre la page et fait le pari de l'étape 3, qui ouvre l'atelier. */
async function ouvrirAtelier(page: Page): Promise<void> {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="temperature"] [data-juste]').click();
  // Fin du fondu d'ouverture (0,35 s) : sinon axe mesurerait un contraste à mi-chemin.
  await expect(page.locator('[data-verrou="atelier"]')).toHaveCSS('opacity', '1');
}

/** Règle le nombre de caractères de contexte au clavier. */
async function reglerN(page: Page, n: number): Promise<void> {
  const nombreJaune = page.locator('[data-test="ml-n"]');
  await nombreJaune.focus();
  await page.keyboard.press('Home');
  for (let i = 0; i < n; i++) await page.keyboard.press('ArrowRight');
  await expect(nombreJaune).toHaveAttribute('aria-valuenow', String(n));
}

/** Les barres de l'atelier : [caractère, chance], lues dans data-caractere et data-chance. */
async function barres(page: Page): Promise<[string, number][]> {
  return page
    .locator('[data-test="ml-distribution"] tr[data-caractere]')
    .evaluateAll((lignes) => lignes.map((l) => [l.getAttribute('data-caractere') ?? '', Number(l.getAttribute('data-chance'))]));
}

/** Les messages de l'atelier, dans l'ordre. */
async function messages(page: Page): Promise<string[]> {
  return page.locator('[data-test="ml-message"]').allTextContents();
}

/** Vérifie les barres, l'ordre utilisé et la suite de l'atelier face au jumeau. */
async function verifierAtelier(page: Page, contexte: string, n: number, temperature: number, graine: number): Promise<void> {
  const [ordre, chances] = tirage(COMPTES, LETTRES, contexte, n, temperature);
  const nom = `contexte ${JSON.stringify(contexte)}, n = ${n}, T = ${temperature}, graine ${graine}`;
  await expect(page.locator('[data-test="ml-distribution"]'), nom).toHaveAttribute('data-ordre', String(ordre));
  expect(await barres(page), nom).toStrictEqual(chances.slice(0, BARRES_MONTREES));
  expect(await texteExact(page, '[data-test="ml-suite"]'), nom).toBe(
    generer(COMPTES, LETTRES, n, contexte, LONGUEUR_SUITE, temperature, graine),
  );
}

test('chapitre 1.1 complet', async ({ page }, info) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  const { total } = trouverChapitre('1.1');
  expect(total).toBe(21);
  await expect(page.locator('header')).toContainText(`Partie 1, chapitre 1.1 sur ${total}`);
  if (info.project.name === 'mobile') expect(page.viewportSize()?.width).toBe(390);
  await expect(page.locator('.pari[data-pari]')).toHaveCount(4);
  await page.locator('[data-pari="suivant"] [data-juste]').click();
  await page.locator('[data-pari="temperature"] [data-juste]').click();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  // Changer le nombre de caractères de contexte fait gagner l'acquis de l'atelier.
  await reglerN(page, N_INITIAL - 1);
  await expect(page.locator('#recap [data-acquis="atelier"]')).toHaveAttribute('data-gagne', 'oui');
  await page.locator('[data-pari="contexte"] [data-juste]').click();
  await page.locator('[data-pari="perplexite"] [data-juste]').click();
  await expect(page.locator('#recap [data-total]')).toContainText('5 sur 5');
  // Le pied suit les fichiers : 1.2 est « à venir » tant qu'il n'a pas paru, 0.5 est un lien.
  await verifierVoisin(page, 'suivant', '1-2.mdx', '/forge-ia/partie-1/1-2/');
  await verifierVoisin(page, 'precedent', '0-5.mdx', '/forge-ia/partie-0/0-5/');
  // Aucun lien vers un chapitre qui n'a pas paru : les renvois à 1.2, 1.4 et 1.5 sont du texte.
  await verifierLiensVersParus(page.locator('main'), PAGE);
  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'), BRUT);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('les choix des paris viennent du jumeau', async ({ page }) => {
  await page.goto(PAGE);
  const paris: [string, Choix[]][] = [
    ['suivant', choixSuivant(TEXTE)],
    ['temperature', choixTemperature(TEXTE)],
    ['contexte', choixContexte(TEXTE)],
    ['perplexite', choixPerplexite(PERPLEXITES)],
  ];
  for (const [id, choix] of paris) {
    const boutons = page.locator(`[data-pari="${id}"] button[data-choix]`);
    expect(await boutons.allTextContents(), id).toEqual(choix.map(affiche));
    expect(await page.locator(`[data-pari="${id}"] [data-juste]`).textContent(), id).toBe(affiche(choix.find((c) => c.juste)!));
  }
  // L'ouverture : les cinq caractères du jumeau, dans l'ordre.
  const o = ouvertureDuChapitre(TEXTE);
  const caracteres = await page
    .locator('[data-test="ouverture"] [data-caractere]')
    .evaluateAll((li) => li.map((e) => e.getAttribute('data-caractere') ?? ''));
  expect(caracteres).toEqual(o.suites.map(([c]) => c));
  // La phrase du minimum : le n et la perplexité du Python.
  const { n, valeur } = minimumDesPerplexites(PERPLEXITES);
  expect(await texteExact(page, '[data-test="minimum"]')).toContain(
    `la plus basse avec ${n} caractères de contexte${FINE}: ${nombre(valeur, 1)}`,
  );
  // Le tableau : une ligne par n, le minimum marqué.
  const lignes = page.locator('[data-test="perplexites"] tbody tr');
  await expect(lignes).toHaveCount(PERPLEXITES.length);
  await expect(page.locator('[data-test="perplexites"] tr[data-minimum]')).toHaveAttribute('data-n', String(n));
  for (const [i, p] of PERPLEXITES.entries()) {
    await expect(lignes.nth(i).locator('td').nth(1)).toHaveText(nombre(p.entrainement, 1));
    await expect(lignes.nth(i).locator('td').nth(2)).toHaveText(nombre(p.validation, 1));
  }
});

test('le code affiché est celui des régions testées', async ({ page }) => {
  await page.goto(PAGE);
  const ngrammes = 'projets/1.1-modele-de-langage/modele_de_langage/ngrammes.py';
  const regions: [string, string][] = [
    [ngrammes, 'compter'],
    [ngrammes, 'distribution'],
    [ngrammes, 'poids'],
    [ngrammes, 'generer'],
    [ngrammes, 'perplexite'],
    ['projets/1.1-modele-de-langage/tests/test_ngrammes.py', 'test-uniforme'],
  ];
  const blocs = page.locator('.code-explique');
  await expect(blocs).toHaveCount(regions.length);
  for (const [i, [fichier, region]] of regions.entries()) {
    const attendu = extraireRegion(readFileSync(`../${fichier}`, 'utf8'), region, fichier);
    expect(await blocs.nth(i).locator('pre').evaluate((pre) => pre.textContent), region).toBe(attendu);
    await expect(blocs.nth(i).locator('figcaption a')).toHaveAttribute(
      'href',
      `https://github.com/chipat-neko/forge-ia/blob/main/${fichier}`,
    );
  }
  await expect(page.getByRole('link', { name: 'Le projet complet' })).toHaveAttribute(
    'href',
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/1.1-modele-de-langage',
  );
});

test('atelier : contexte jamais vu, contexte trop court, champ vide, emoji, température 0', async ({ page }) => {
  await ouvrirAtelier(page);
  const champ = page.locator('[data-test="ml-contexte"]');
  const atelier = page.locator('[data-atelier]');

  // À l'arrivée, aucun message.
  expect(await messages(page)).toEqual([]);

  // Un contexte trop court : rien n'est tiré.
  await champ.fill('Le');
  expect(await messages(page)).toEqual([messageCourt(N_INITIAL)]);
  expect(messageCourt(N_INITIAL)).toBe(`Il faut au moins ${N_INITIAL} caractères de contexte${FINE}: écris-en un peu plus.`);
  await expect(page.locator('[data-test="ml-distribution"]')).toHaveCount(0);
  await expect(page.locator('[data-test="ml-suite"]')).toHaveCount(0);

  // Le champ vide : le même message ; à n = 0, le modèle tire sans contexte.
  await champ.fill('');
  expect(await messages(page)).toEqual([messageCourt(N_INITIAL)]);
  await reglerN(page, 0);
  expect(await messages(page)).toEqual([]);
  await verifierAtelier(page, '', 0, TEMPERATURE_INITIALE, GRAINE_INITIALE);

  // Un contexte jamais vu : le modèle raccourcit son contexte, et le dit.
  await reglerN(page, N_INITIAL);
  await champ.fill('Le forgeron qzxw');
  const [ordre] = tirage(COMPTES, LETTRES, 'Le forgeron qzxw', N_INITIAL, TEMPERATURE_INITIALE);
  expect(ordre).toBeLessThan(N_INITIAL);
  expect(await messages(page)).toEqual([messageRecul(ordre)]);
  expect(messageRecul(ordre)).toBe(
    `Ce contexte n’apparaît jamais dans le texte${FINE}: le modèle raccourcit son contexte à ${ordre} ` +
      `${ordre > 1 ? 'caractères' : 'caractère'}, le plus long qu’il connaît.`,
  );
  await verifierAtelier(page, 'Le forgeron qzxw', N_INITIAL, TEMPERATURE_INITIALE, GRAINE_INITIALE);

  // Un emoji compte pour un caractère, et n'a jamais été vu : le modèle recule jusqu'à 0.
  await champ.fill('Le forgeron 😀');
  expect(await messages(page)).toEqual([messageRecul(0)]);
  await verifierAtelier(page, 'Le forgeron 😀', N_INITIAL, TEMPERATURE_INITIALE, GRAINE_INITIALE);
  await champ.fill('😀😀😀');
  expect(await messages(page)).toEqual([messageCourt(N_INITIAL)]);

  // Température 0 sur le contexte du départ : la suite tourne en rond, et le message le dit.
  await champ.fill(CONTEXTE_INITIAL);
  await page.locator('[data-test="ml-t-0"]').click();
  await expect(page.locator('[data-test="ml-t-0"]')).toHaveAttribute('aria-pressed', 'true');
  expect(await messages(page)).toEqual([messageBoucle()]);
  expect(etatDeLAtelier(COMPTES, LETTRES, CONTEXTE_INITIAL, N_INITIAL, 0, GRAINE_INITIALE).messages).toEqual([messageBoucle()]);
  await verifierAtelier(page, CONTEXTE_INITIAL, N_INITIAL, 0, GRAINE_INITIALE);

  // Le recalcul après une frappe tient en moins de 200 ms (médiane de 5 essais).
  const durees: number[] = [];
  for (let essai = 0; essai < 5; essai++) {
    durees.push(
      await page.evaluate(async (texte) => {
        const champ = document.querySelector<HTMLInputElement>('[data-test="ml-contexte"]')!;
        const debut = performance.now();
        champ.value = texte;
        champ.dispatchEvent(new Event('input', { bubbles: true }));
        // Svelte met la page à jour avant la prochaine image.
        await new Promise((fin) => requestAnimationFrame(() => fin(null)));
        return performance.now() - debut;
      }, `${CONTEXTE_INITIAL} ${'abcdefghij'[essai]}`),
    );
  }
  durees.sort((a, b) => a - b);
  expect(durees[2], `durées en ms : ${durees.map((d) => d.toFixed(1)).join(', ')}`).toBeLessThan(200);

  // Un texte collé de 400 caractères sans espace passe à la ligne, sans élargir la page.
  await champ.fill('a'.repeat(400));
  await verifierSansDebordement(page);
  // Jamais de valeur absurde dans l'atelier.
  expect(await atelier.innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
});

test('atelier : distribution et suite égales au jumeau pour n = 0 à 6', async ({ page }) => {
  await ouvrirAtelier(page);
  // À l'arrivée : n = 4, température 1, graine 0.
  await expect(page.locator('[data-test="ml-n"]')).toHaveAttribute('aria-valuenow', String(N_INITIAL));
  await expect(page.locator(`[data-test="ml-t-${TEMPERATURE_INITIALE}"]`)).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('[data-test="ml-contexte"]')).toHaveValue(CONTEXTE_INITIAL);
  await verifierAtelier(page, CONTEXTE_INITIAL, N_INITIAL, TEMPERATURE_INITIALE, GRAINE_INITIALE);
  // Chaque n, de 0 à 6, à la température du départ.
  for (let n = 0; n <= N_MAX; n++) {
    await reglerN(page, n);
    await verifierAtelier(page, CONTEXTE_INITIAL, n, TEMPERATURE_INITIALE, GRAINE_INITIALE);
  }
  // Chaque température, à n = 4.
  await reglerN(page, N_INITIAL);
  for (const t of TEMPERATURES_ATELIER) {
    await page.locator(`[data-test="ml-t-${t}"]`).click();
    await verifierAtelier(page, CONTEXTE_INITIAL, N_INITIAL, t, GRAINE_INITIALE);
  }
  // La commande du projet et l'atelier écrivent le même texte, à la graine du départ (étape 9).
  await page.locator(`[data-test="ml-t-${TEMPERATURE_INITIALE}"]`).click();
  await page.locator('[data-test="ml-contexte"]').fill('Le forgeron ');
  await verifierAtelier(page, 'Le forgeron ', N_INITIAL, TEMPERATURE_INITIALE, GRAINE_INITIALE);
  // « Tirer encore » : la graine suivante.
  await page.locator('[data-test="ml-tirer"]').click();
  await verifierAtelier(page, 'Le forgeron ', N_INITIAL, TEMPERATURE_INITIALE, GRAINE_INITIALE + 1);
  // Le défi : un contexte dont le suivant le plus probable est une espace.
  const defi = page.locator('[data-defi]');
  await expect(defi).not.toHaveClass(/\breussi\b/);
  await page.locator('[data-test="ml-contexte"]').fill('les questions');
  await expect(defi).toHaveClass(/\breussi\b/);
  expect(await texteExact(page, '[data-test="ml-defi"]')).toBe(
    `Défi réussi${FINE}: après «${FINE}ions${FINE}», le caractère le plus probable est une espace.`,
  );
  await expect(defi.locator('[role="status"]')).toContainText('Défi réussi');
  await verifierAxe(page);
});

test('avant le pari, l’atelier est verrouillé ; sans JavaScript, tout se lit', async ({ page, browser, baseURL }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await expect(page.locator('[data-verrou="atelier"]')).toHaveAttribute('inert', '');
  await expect(page.locator('.verrou-msg')).toContainText('Fais ton pari à l’étape 3');
  await expect(page.locator('[data-test="ml-n"]')).toHaveAttribute('aria-disabled', 'true');
  await verifierAxe(page);
  await verifierSansDebordement(page);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);

  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const sansJs = await ctx.newPage();
  await sansJs.goto(PAGE);
  // Pas de verrou : l'atelier est là, net, avec ses valeurs de départ.
  await expect(sansJs.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(sansJs.locator('[data-test="ml-contexte"]')).toHaveValue(CONTEXTE_INITIAL);
  await verifierAtelier(sansJs, CONTEXTE_INITIAL, N_INITIAL, TEMPERATURE_INITIALE, GRAINE_INITIALE);
  await expect(sansJs.locator('[data-test="ml-suite"]')).toBeVisible();
  // Les explications des paris sont données d'emblée.
  for (const id of ['suivant', 'temperature', 'contexte', 'perplexite']) {
    await expect(sansJs.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  }
  await expect(sansJs.locator('[data-test="ouverture"]')).toBeVisible();
  await expect(sansJs.locator('[data-test="perplexites"]')).toBeVisible();
  await ctx.close();
});
