// Parcours du chapitre 0.2, « Les maths utiles », en entier : un brouillon
// (src/brouillons/chapitres/0-2.mdx) tant qu'il n'a pas paru, construit à son
// adresse définitive avec FORGE_ESSAIS=1. Les figures ont leur propre parcours
// (figures-0-2.spec.ts) ; celui-ci vérifie le chapitre : ses paris, ses
// tableaux, son code, son récapitulatif, son pied et sa lecture.
//
// Les attendus viennent du jumeau (maths.ts), des paris (paris-0-2.ts), et des
// fichiers du Python lus sur le disque : un parcours, chargé par Node sans
// Vite, n'importe aucun module à ?raw, .json ou astro:* (B1). Softmax et −ln p
// ne sont jamais recalculés : les tableaux doivent montrer les valeurs du
// Python, mises en forme. Les valeurs clés sont aussi écrites ici en toutes
// lettres, pour ne pas seulement comparer le module à lui-même.
import { existsSync, readFileSync } from 'node:fs';
import { test, expect, type Locator, type Page } from '@playwright/test';
import { formaterPuissanceDeDix, formaterQuantite } from '../src/lib/calculateur/formats';
import { modelePublic } from '../src/lib/calculateur/donnees';
import { extraireRegion } from '../src/lib/regions';
import { trouverChapitre } from '../src/lib/parcours';
import type { Choix } from '../src/lib/choix';
import { nombre } from '../src/lib/nombres';
import { matriceFoisVecteur, produitScalaire } from '../src/lib/partie-0/maths';
import {
  A_DEPART,
  B_DEPART,
  choixErreur,
  choixFormeMatrice,
  choixPente,
  choixProduitScalaire,
  choixTauxGrand,
  choixTauxMoitie,
  choixTirage,
  faitsChaine,
  MATRICE_EXEMPLE,
  tableauErreur,
  tableauMatrice,
  tableauSoftmax,
  texteOuverture,
  VECTEUR_EXEMPLE,
  type ChaineAttendue,
  type ErreurAttendue,
  type SoftmaxAttendu,
} from '../src/lib/partie-0/paris-0-2';
import { typographier } from '../src/lib/typo';
import {
  attendreHydratation,
  plusLongueLigne,
  verifierAxe,
  verifierLiensVersParus,
  verifierSansDebordement,
  verifierTypographieHorsCode,
} from './outils';

const PAGE = '/forge-ia/partie-0/0-2/';
const FINE = '\u202F';
const INSECABLE = '\u00A0';

// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
const ATTENDUS = JSON.parse(readFileSync('../projets/0.2-maths/tests/attendus.json', 'utf8')) as {
  matrices: { m: number[][]; v: number[]; resultat: number[] | null }[];
  chaine: ChaineAttendue;
  softmax: SoftmaxAttendu[];
  erreur: ErreurAttendue[];
};
/** Le vocabulaire du mini-modèle, V : les caractères écrits par son Python (donnees.test.ts le relie au TypeScript). */
const V = Array.from(
  (JSON.parse(readFileSync('../projets/mini-modele/tests/attendus-donnees.json', 'utf8')) as { vocabulaire: string })
    .vocabulaire,
).length;

/** Les titres des huit étapes, dans l'ordre. */
const TITRES = [
  'Des nombres en colonne : les vecteurs',
  'Les matrices : beaucoup de produits scalaires',
  'La pente',
  'Descendre la pente',
  'La règle de la chaîne',
  'Les probabilités',
  'Des scores aux probabilités, et l’erreur',
  'À grande échelle',
];

/** Les paris du chapitre, dans l'ordre de la page, avec leurs choix calculés. */
const PARIS: [string, Choix[]][] = [
  ['scalaire', choixProduitScalaire()],
  ['formes', choixFormeMatrice()],
  ['pente', choixPente()],
  ['taux-moitie', choixTauxMoitie()],
  ['taux-grand', choixTauxGrand()],
  ['tirage', choixTirage()],
  ['erreur', choixErreur(ATTENDUS.erreur, V)],
];

/** Le texte d'un choix tel qu'un bouton l'affiche : le code tel quel, le reste typographié. */
function affiche(choix: Choix): string {
  return choix.texte
    .split('`')
    .map((morceau, i) => (i % 2 === 1 ? morceau : typographier(morceau)))
    .join('');
}

/** Le texte exact d'un élément (textContent : toHaveText ramènerait U+202F à une espace ordinaire). */
async function texteExact(zone: Locator): Promise<string> {
  return (await zone.textContent()) ?? '';
}

/** Les cellules d'un tableau, ligne par ligne (en-têtes de ligne compris), en texte exact. */
async function cellules(tableau: Locator, partie: 'thead' | 'tbody' = 'tbody'): Promise<string[][]> {
  return tableau
    .locator(`${partie} tr`)
    .evaluateAll((lignes) => lignes.map((tr) => [...tr.querySelectorAll('th, td')].map((c) => c.textContent ?? '')));
}

/** Attend la fin des animations en cours (fondu du verrou, verdict des paris) : axe mesure alors les vraies couleurs. */
async function attendreAnimations(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)).then(() => undefined));
}

/** Règle un nombre jaune au clavier sur une valeur (aria-valuenow), par les flèches. */
async function regler(nombreJaune: Locator, valeur: number): Promise<void> {
  await nombreJaune.focus();
  const actuelle = Number(await nombreJaune.getAttribute('aria-valuenow'));
  for (let i = 0; i < Math.abs(valeur - actuelle); i++) await nombreJaune.press(valeur > actuelle ? 'ArrowRight' : 'ArrowLeft');
  await expect(nombreJaune).toHaveAttribute('aria-valuenow', String(valeur));
}

/** Le pied vers un voisin : un lien s'il a paru (son fichier est dans src/content/chapitres/), sinon « à venir » (S2). */
async function verifierVoisin(page: Page, sens: 'precedent' | 'suivant', fichier: string, href: string): Promise<void> {
  const voisin = page.locator(`footer .voisin.${sens}`);
  if (existsSync(`src/content/chapitres/${fichier}`)) {
    await expect(voisin).toHaveAttribute('href', href);
  } else {
    await expect(voisin).toContainText('à venir');
    await expect(page.locator(`footer a.voisin.${sens}`)).toHaveCount(0);
  }
}

test('chapitre 0.2 complet', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  const { total } = trouverChapitre('0.2');
  await expect(page.locator('header')).toContainText(`Partie 0, chapitre 0.2 sur ${total}`);
  // Huit étapes, dans l'ordre, et sept paris.
  const titres = page.locator('.etape h2');
  await expect(titres).toHaveCount(TITRES.length);
  expect(await titres.evaluateAll((h) => h.map((e) => e.textContent))).toEqual(TITRES.map(typographier));
  await expect(page.locator('[data-pari]')).toHaveCount(PARIS.length);
  await expect(page.locator('#recap [data-acquis]')).toHaveCount(7);

  // Tous les paris, dans l'ordre de la page.
  for (const [id] of PARIS) await page.locator(`[data-pari="${id}"] [data-juste]`).click();
  await expect(page.locator('[data-verrou="vecteurs"]')).not.toHaveAttribute('inert', '');
  // Le défi : deux vecteurs perpendiculaires, (2, 1) et (−1, 2), réglés dans la figure.
  await regler(page.locator('[data-test="vec-ax"]'), 2);
  await regler(page.locator('[data-test="vec-bx"]'), -1);
  expect(produitScalaire([2, A_DEPART[1]], [-1, B_DEPART[1]])).toBe(0);
  await expect(page.locator('#recap [data-acquis="perpendiculaires"]')).toHaveAttribute('data-gagne', 'oui');
  // Les six acquis des paris et celui du défi : tout est gagné.
  await expect(page.locator('#recap [data-gagne="oui"]')).toHaveCount(7);
  await expect(page.locator('#recap [data-total]')).toContainText('7 sur 7');

  // Le pied suit les fichiers : 0.1 et 0.3 sont « à venir » tant qu'ils n'ont pas paru (S2).
  await verifierVoisin(page, 'precedent', '0-1.mdx', '/forge-ia/partie-0/0-1/');
  await verifierVoisin(page, 'suivant', '0-3.mdx', '/forge-ia/partie-0/0-3/');
  // Aucun lien vers un chapitre qui n'a pas paru (S3) : les renvois à 0.1, 0.3, 0.4 et 0.5 sont du texte.
  await verifierLiensVersParus(page.locator('main'), PAGE);

  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'));
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
  // Jamais de valeur absurde, ni de « −0 » ou « −0,000 ».
  expect(await page.locator('main').innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+|[-−]0(?:,0*)?(?![,\d])/);
});

test('les choix des paris viennent du jumeau et des attendus', async ({ page }) => {
  await page.goto(PAGE);
  for (const [id, choix] of PARIS) {
    const boutons = page.locator(`[data-pari="${id}"] button[data-choix]`);
    expect(await boutons.allTextContents(), id).toEqual(choix.map(affiche));
    expect(await page.locator(`[data-pari="${id}"] [data-juste]`).textContent(), id).toBe(
      affiche(choix.find((c) => c.juste)!),
    );
  }
  // Le pari « erreur », en toutes lettres : une chance sur 40, ln 40 = 3,689.
  expect(V).toBe(40);
  expect(choixErreur(ATTENDUS.erreur, V).map((c) => c.texte)).toEqual(['0,025', '3,689', '40']);
  expect(await texteExact(page.locator('[data-pari="erreur"] .q'))).toContain(`une chance sur ${V}`);
  // Le pari « formes » : une matrice de 3 lignes et 4 colonnes, 4 le juste.
  expect(await texteExact(page.locator('[data-pari="formes"] .q'))).toContain('3 lignes et 4 colonnes');
  await expect(page.locator('[data-pari="formes"] [data-juste]')).toHaveText('4');
});

test('l’ouverture et les tableaux viennent du jumeau et des attendus du Python', async ({ page }) => {
  await page.goto(PAGE);
  // L'ouverture : (3, 1) · (1, 2) = 5, calculé par le jumeau.
  expect(texteOuverture()).toBe(`(3,${INSECABLE}1) · (1,${INSECABLE}2) = 5`);
  expect(await texteExact(page.locator('[data-test="ouverture-calcul"]'))).toBe(texteOuverture());
  expect(await texteExact(page.locator('[data-test="ouverture"]'))).toContain(
    typographier('ton IA ne fait rien d’autre, des milliards de fois'),
  );

  // Étape 2 : la matrice de l'exemple, une ligne du tableau par ligne de la matrice.
  expect(matriceFoisVecteur(MATRICE_EXEMPLE, VECTEUR_EXEMPLE)).toEqual(ATTENDUS.matrices[0].resultat);
  expect(ATTENDUS.matrices[0].resultat).toEqual([6, 1]);
  const matrice = page.locator('[data-test="matrice-exemple"]');
  expect(await cellules(matrice)).toEqual(tableauMatrice(MATRICE_EXEMPLE, VECTEUR_EXEMPLE));
  expect((await cellules(matrice)).map((l) => l.at(-1))).toEqual(['6', '1']);

  // Étape 5 : la règle de la chaîne, avec les valeurs du Python.
  const chaine = faitsChaine(ATTENDUS.chaine);
  expect(chaine.exacte).toBe('12');
  expect(chaine.approchee).toBe('11,9999999999');
  const etape5 = await texteExact(page.locator('#etape-5 .texte'));
  for (const morceau of [`${chaine.penteExterieur} × ${chaine.penteInterieur} = ${chaine.exacte}`, chaine.approchee]) {
    expect(etape5).toContain(morceau);
  }

  // Étape 7 : softmax et −ln p, les valeurs du Python mises en forme, jamais recalculées.
  const softmax = page.locator('[data-test="softmax"]');
  const attenduSoftmax = tableauSoftmax(ATTENDUS.softmax);
  expect((await cellules(softmax, 'thead'))[0]).toEqual(['Température', ...attenduSoftmax.colonnes]);
  expect(await cellules(softmax)).toEqual(attenduSoftmax.lignes);
  expect((await cellules(softmax))[0]).toEqual(['0,5', `86,4${FINE}%`, `11,7${FINE}%`, `1,9${FINE}%`]);
  const erreurs = page.locator('[data-test="erreurs"]');
  expect(await cellules(erreurs)).toEqual(tableauErreur(ATTENDUS.erreur));
  expect((await cellules(erreurs)).at(-1)).toEqual(['0,025', '40', '3,689']);
  // −ln 1 vaut −0.0 dans les attendus : le tableau écrit 0, sans signe.
  expect(Object.is(ATTENDUS.erreur[0].erreur, -0)).toBe(true);
  expect((await cellules(erreurs))[0]).toEqual(['1', '1', '0,000']);
  expect(await texteExact(erreurs)).not.toMatch(/[-−]0/);

  // Étape 8 : 6 × N × D pour Llama 3 405B, et ses matrices de dim × dim poids.
  const llama = modelePublic('llama-3-405b');
  const labo = await texteExact(page.locator('#etape-8 .labo'));
  expect(labo).toContain(formaterPuissanceDeDix(6 * llama.parametres * llama.jetonsOrigine));
  expect(labo).toContain(`${nombre(llama.dim)} lignes et ${nombre(llama.dim)} colonnes`);
  expect(labo).toContain(formaterQuantite(llama.dim * llama.dim));
  // Ce que Meta annonce, lu dans les données du calculateur.
  expect(llama.operationsPubliees).toBe(3.8e25);
  expect(labo).toContain(`Meta annonce 3,8${FINE}×${FINE}10²⁵`);
});

test('le code affiché est celui des régions testées', async ({ page }) => {
  await page.goto(PAGE);
  const regions: [string, string][] = [
    ['projets/0.2-maths/maths_utiles/vecteurs.py', 'scalaire'],
    ['projets/0.2-maths/maths_utiles/vecteurs.py', 'matrice'],
    ['projets/0.2-maths/maths_utiles/derivees.py', 'erreur'],
    ['projets/0.2-maths/maths_utiles/derivees.py', 'pente'],
    ['projets/0.2-maths/maths_utiles/derivees.py', 'descendre'],
    ['projets/0.2-maths/maths_utiles/derivees.py', 'chaine'],
    ['projets/0.2-maths/maths_utiles/tirage.py', 'tirer'],
    ['projets/0.2-maths/maths_utiles/tirage.py', 'hasard'],
    ['projets/0.2-maths/maths_utiles/probabilites.py', 'softmax'],
    ['projets/0.2-maths/maths_utiles/probabilites.py', 'erreur-de-prediction'],
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
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/0.2-maths',
  );
  await expect(page.getByRole('link', { name: 'Ouvrir dans Colab' })).toHaveAttribute(
    'href',
    'https://colab.research.google.com/github/chipat-neko/forge-ia/blob/main/notebooks/0.2-maths.ipynb',
  );
});

test('sans JavaScript, tout le chapitre se lit', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  await expect(page.locator('[data-test="ouverture"]')).toBeVisible();
  for (const test of ['matrice-exemple', 'softmax', 'erreurs']) {
    await expect(page.locator(`[data-test="${test}"]`)).toBeVisible();
  }
  expect((await cellules(page.locator('[data-test="erreurs"]'))).at(-1)).toEqual(['0,025', '40', '3,689']);
  // Les explications des sept paris sont données d'emblée.
  for (const [id] of PARIS) await expect(page.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  await expect(page.locator('#etape-8 .labo')).toBeVisible();
  await verifierSansDebordement(page);
  await ctx.close();
});
