// Parcours du chapitre 0.4, « Tenseurs et calcul sur GPU » : un brouillon
// (src/brouillons/chapitres/0-4.mdx) tant qu'il n'a pas paru, construit à son
// adresse définitive avec FORGE_ESSAIS=1.
//
// Les attendus viennent du jumeau des formes (formes.ts, vérifié contre
// PyTorch), de l'atelier (atelier-formes.ts), des paris (paris-0-4.ts), des
// mesures lues sur le disque par mesures.ts (projets/0.4-tenseurs/mesures/),
// des commandes (commandes.ts) et des données du calculateur. Ces modules sont
// purs, ou ne lisent le disque que par node:fs : un parcours, chargé par Node
// sans Vite, peut les importer (B1). Les attendus du projet (attendus-formes.json,
// 210 Ko) sont lus par readFileSync, jamais importés.
//
// Les chronos du processeur et de la carte ont été relevés à la porte de la
// Partie 0, carte au repos (le 5 novembre 2026), et pourraient l'être encore :
// rien ici ne fige une durée, tout se recalcule depuis les fichiers. Le
// chapitre n'a plus aucune valeur « à mesurer » : le fichier de la carte doit
// être là.
import { existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { test, expect, type Locator, type Page } from '@playwright/test';
import { materiel, REPERES_EFFICACITE } from '../src/lib/calculateur/donnees';
import { formaterDate, formaterOctets } from '../src/lib/calculateur/formats';
import { memoirePoidsOctets } from '../src/lib/calculateur/formules';
import { MESURES_TON_IA, PRESETS_FORGE } from '../src/lib/calculateur/ton-ia';
import { enGo, OCTETS_ROUE_CU132_WINDOWS } from '../src/lib/partie-0/sources-0-3';
import { nombre, pourcent } from '../src/lib/nombres';
import { trouverChapitre } from '../src/lib/parcours';
import { extraireRegion } from '../src/lib/regions';
import { typographier } from '../src/lib/typo';
import { A_DEPART, B_DEPART, DEFI_FORMES_REUSSI, expliquer, type Operation } from '../src/lib/partie-0/atelier-formes';
import * as commandes from '../src/lib/partie-0/commandes';
import { ecrireForme, formeDiffusee, formeProduit } from '../src/lib/partie-0/formes';
import { FICHIERS_MESURES, lireMesures, type MesuresChrono } from '../src/lib/partie-0/mesures';
import {
  choixDiffusion,
  choixFils,
  choixMemoire,
  choixPetiteMatrice,
  ecrireMillisecondes,
  explicationPetite,
  phraseCarteEtProcesseur,
  phraseFils,
  phraseTransfert,
  questionFils,
  questionPetite,
} from '../src/lib/partie-0/paris-0-4';
import {
  attendreHydratation,
  plusLongueLigne,
  verifierAxe,
  verifierLiensVersParus,
  verifierSansDebordement,
  verifierTypographieHorsCode,
} from './outils';

const PAGE = '/forge-ia/partie-0/0-4/';
/** --corail de jetons.css (#B8342D), tel que le navigateur le calcule. */
const CORAIL = 'rgb(184, 52, 45)';
const FINE = '\u202F';

// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
const RACINE = resolve('..');
const PROCESSEUR = lireMesures('processeur', RACINE)!;
const CARTE_LUE = lireMesures('rtx-5070-ti', RACINE);
if (CARTE_LUE === null) {
  throw new Error(
    `${FICHIERS_MESURES['rtx-5070-ti']} manque : le chapitre 0.4 a besoin des chronos de la carte (pari « petite », ` +
      'tableau, phrases de l’étape 6). Mesure-la avec « uv run --extra gpu python -m tenseurs mesurer --appareil cuda ' +
      '--sortie mesures/rtx-5070-ti.json », dans projets/0.4-tenseurs, carte au repos.',
  );
}
const CARTE: MesuresChrono = CARTE_LUE;
const ATTENDUS = JSON.parse(readFileSync('../projets/0.4-tenseurs/tests/attendus-formes.json', 'utf8')) as {
  exemples: { creer: Record<string, { forme: number[] }> };
};

/** Les titres des huit étapes, dans l'ordre. */
const TITRES = [
  'Des nombres rangés en dimensions',
  'Créer et lire',
  'Calculer',
  'La diffusion',
  'Les types de nombres et la mémoire',
  'Sur la carte',
  'Les fils du processeur',
  'À grande échelle',
];
/** Les paris, dans l'ordre de la page : `petite` est à l'étape 6, avant le tableau des chronos. */
const PARIS = ['diffusion', 'memoire', 'petite', 'fils'];
/** Les acquis, dans l'ordre du chapitre ; le texte de `fils` est celui de la décision du contrôleur (ronde 1). */
const ACQUIS: [string, string][] = [
  ['diffusion', "Une dimension de taille 1 s'étire pour suivre l'autre."],
  ['formes', 'Pour A @ B, les colonnes de A doivent égaler les lignes de B.'],
  ['memoire', "La mémoire d'un tenseur, c'est son nombre de cases fois la taille d'un nombre."],
  ['petite', 'Pour un petit calcul, la carte ne gagne pas toujours.'],
  ['fils', 'Le processeur aussi calcule en parallèle, sur plusieurs fils ; pour les prendre tous, il faut le demander.'],
];
const NB_ACQUIS = ACQUIS.length;

/** Les commandes que les blocs « À taper » du chapitre montrent, dans l'ordre de la page. */
const COMMANDES_DES_BLOCS = [
  // Le dépôt déjà téléchargé au chapitre 0.1 se met à jour ; sinon, on le télécharge.
  [commandes.METTRE_A_JOUR_DEPOT, commandes.ALLER_AU_PROJET_0_4],
  [commandes.CLONER_DEPOT, commandes.ALLER_AU_PROJET_0_4],
  [commandes.TENSEURS_FORMES],
  [commandes.TENSEURS_MESURER_CPU],
  [commandes.TENSEURS_MESURER_GPU],
];

/** Les régions de code montrées, dans l'ordre de la page. */
const REGIONS: [string, string][] = [
  ['projets/0.4-tenseurs/tenseurs/exemples.py', 'creer'],
  ['projets/0.4-tenseurs/tenseurs/exemples.py', 'lire'],
  ['projets/0.4-tenseurs/tenseurs/exemples.py', 'calculer'],
  ['projets/0.4-tenseurs/tenseurs/formes.py', 'diffusion'],
  ['projets/0.4-tenseurs/tenseurs/formes.py', 'produit'],
  ['projets/0.4-tenseurs/tenseurs/memoire.py', 'memoire'],
  ['projets/0.4-tenseurs/tenseurs/appareil.py', 'appareil'],
  ['projets/0.4-tenseurs/tenseurs/chrono.py', 'chrono'],
  ['projets/0.4-tenseurs/tenseurs/chrono.py', 'transfert'],
];

/** Le texte exact d'un élément (textContent : toHaveText ramènerait U+202F à une espace ordinaire). */
async function texteExact(zone: Locator): Promise<string> {
  return (await zone.textContent()) ?? '';
}

/** Les blancs du balisage (espaces, retours à la ligne) ramenés à une espace ; U+202F reste tel quel. */
function sansBlancsDeBalisage(texte: string): string {
  return texte.replace(/[ \n\t]+/g, ' ').trim();
}

/** Attend la fin des animations en cours (fondu du verrou, verdict des paris) : axe mesure alors les vraies couleurs. */
async function attendreAnimations(page: Page): Promise<void> {
  await page.evaluate(() => Promise.all(document.getAnimations().map((a) => a.finished)).then(() => undefined));
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

/** Règle un nombre jaune au clavier sur une valeur (aria-valuenow), par les flèches. */
async function regler(nombre: Locator, valeur: number): Promise<void> {
  await nombre.focus();
  const actuelle = Number(await nombre.getAttribute('aria-valuenow'));
  for (let i = 0; i < Math.abs(valeur - actuelle); i++) await nombre.press(valeur > actuelle ? 'ArrowRight' : 'ArrowLeft');
  await expect(nombre).toHaveAttribute('aria-valuenow', String(valeur));
}

/** Règle A, B et l'opération de l'atelier au clavier : les dimensions, puis chaque taille, puis la bascule. */
async function reglerFormes(page: Page, a: number[], b: number[], op: Operation): Promise<void> {
  for (const [nom, forme] of [
    ['a', a],
    ['b', b],
  ] as const) {
    await regler(page.locator(`[data-test="formes-${nom}-dims"]`), forme.length);
    await expect(page.locator(`[data-test^="formes-${nom}-"]:not([data-test="formes-${nom}-dims"])`)).toHaveCount(forme.length);
    for (const [i, t] of forme.entries()) await regler(page.locator(`[data-test="formes-${nom}-${i}"]`), t);
  }
  const bascule = page.locator(`[data-test="formes-op-${op}"]`);
  await bascule.focus();
  await page.keyboard.press('Enter');
  await expect(bascule).toHaveAttribute('aria-pressed', 'true');
}

/** Le résultat attendu, d'après le jumeau des formes seul. */
function resultatAttendu(a: number[], b: number[], op: Operation): string {
  const r = op === 'plus' ? formeDiffusee(a, b) : formeProduit(a, b);
  return r === null ? 'impossible' : ecrireForme(r);
}

/**
 * Les cases étirées d'A + B, recalculées ici : alignées par la droite, une taille 1 (ou une dimension
 * qui manque) sous un résultat plus grand que 1. « a2 » : la rangée de A, colonne 2 (la plus à droite).
 */
function etireesAttendues(a: number[], b: number[]): string[] {
  const r = formeDiffusee(a, b);
  if (r === null) return [];
  const n = r.length;
  const cases: string[] = [];
  for (const [nom, f] of [
    ['a', a],
    ['b', b],
  ] as const) {
    for (let j = 0; j < n; j++) {
      const taille = j < f.length ? f[f.length - 1 - j] : 1;
      if (taille === 1 && r[n - 1 - j] > 1) cases.push(`${nom}${2 - j}`);
    }
  }
  return cases.sort();
}

/** La durée d'un produit dans un fichier de mesures. */
function ms(m: MesuresChrono, taille: number, fils: number | null): number {
  const x = m.mesures.find((y) => y.taille === taille && y.fils === fils);
  if (!x) throw new Error(`pas de mesure ${taille} / ${fils} dans ${m.nom}`);
  return x.millisecondes;
}

test('chapitre 0.4 complet', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  const { total } = trouverChapitre('0.4');
  await expect(page.locator('header')).toContainText(`Partie 0, chapitre 0.4 sur ${total}`);
  // Huit étapes, dans l'ordre, quatre paris et cinq acquis ; le programme les compte.
  const titres = page.locator('.etape h2');
  await expect(titres).toHaveCount(TITRES.length);
  expect(await titres.evaluateAll((h) => h.map((e) => e.textContent))).toEqual(TITRES.map(typographier));
  expect(await texteExact(page.locator('.programme'))).toContain(`${TITRES.length} étapes, ${PARIS.length} paris`);
  await expect(page.locator('[data-pari]')).toHaveCount(PARIS.length);
  expect(await page.locator('[data-pari]').evaluateAll((p) => p.map((e) => e.getAttribute('data-pari')))).toEqual(PARIS);
  await expect(page.locator('#recap [data-acquis]')).toHaveCount(NB_ACQUIS);
  for (const [cle, texte] of ACQUIS) {
    expect(await texteExact(page.locator(`#recap [data-acquis="${cle}"]`)), cle).toContain(typographier(texte));
  }

  // Avant le pari « diffusion », l'atelier est verrouillé : ses nombres et ses bascules ne répondent pas.
  await expect(page.locator('[data-verrou="formes"]')).toHaveAttribute('inert', '');
  await expect(page.locator('[data-test="formes-a-0"]')).toHaveAttribute('aria-disabled', 'true');
  await expect(page.locator('[data-test="formes-op-produit"]')).toBeDisabled();
  for (const id of PARIS) await page.locator(`[data-pari="${id}"] [data-juste]`).click();
  await expect(page.locator('[data-verrou="formes"]')).not.toHaveAttribute('inert', '');
  await expect(page.locator('[data-verrou="formes"]')).toHaveCSS('opacity', '1');
  await expect(page.locator('#recap [data-gagne="oui"]')).toHaveCount(PARIS.length);

  // L'atelier : un produit A @ B possible, avec un A à 3 dimensions, gagne le dernier acquis.
  await reglerFormes(page, [3, 1, 4], [4], 'produit');
  await expect(page.locator('[data-test="formes-resultat"]')).toHaveText('(3, 1)');
  await expect(page.locator('#recap [data-gagne="oui"]')).toHaveCount(NB_ACQUIS);
  await expect(page.locator('#recap [data-total]')).toContainText(`${NB_ACQUIS} sur ${NB_ACQUIS}`);

  // Le pied suit les fichiers : 0.3 et 0.5 sont « à venir » tant qu'ils n'ont pas paru (S2).
  await verifierVoisin(page, 'precedent', '0-3.mdx', '/forge-ia/partie-0/0-3/');
  await verifierVoisin(page, 'suivant', '0-5.mdx', '/forge-ia/partie-0/0-5/');
  // Aucun lien vers un chapitre qui n'a pas paru (S3) : les renvois à 0.2, 0.3 et 0.5 sont du texte.
  await verifierLiensVersParus(page.locator('main'), PAGE);

  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'));
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
  expect(await page.locator('main').innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
});

test('les choix des paris viennent du jumeau des formes et des mesures', async ({ page }) => {
  await page.goto(PAGE);
  const attendus: Record<string, { texte: string; juste?: boolean }[]> = {
    diffusion: choixDiffusion(),
    memoire: choixMemoire(),
    petite: choixPetiteMatrice(PROCESSEUR, CARTE),
    fils: choixFils(PROCESSEUR),
  };
  for (const id of PARIS) {
    const boutons = page.locator(`[data-pari="${id}"] button[data-choix]`);
    expect(await boutons.allTextContents(), id).toEqual(attendus[id].map((c) => typographier(c.texte)));
    const juste = attendus[id].find((c) => c.juste)!;
    expect(await page.locator(`[data-pari="${id}"] [data-juste]`).textContent(), id).toBe(typographier(juste.texte));
  }
  // Les bonnes réponses, recalculées ici : (3, 1) + (4,) = (3, 4) ; 4 096² × 4 octets = 64 × 2²⁰ octets.
  expect(ecrireForme(formeDiffusee(A_DEPART, B_DEPART)!)).toBe('(3, 4)');
  expect(await page.locator('[data-pari="diffusion"] [data-juste]').textContent()).toBe('(3, 4)');
  expect((4096 * 4096 * 4) / 2 ** 20).toBe(64);
  expect(await page.locator('[data-pari="memoire"] [data-juste]').textContent()).toBe('64 Mo');
  // Les fils : le rapport des chronos du fichier, au réglage par défaut et avec tous les fils.
  const r = ms(PROCESSEUR, 4096, PROCESSEUR.fils_par_defaut) / ms(PROCESSEUR, 4096, PROCESSEUR.fils_max);
  const verdict = r >= 1.8 ? 'Deux fois plus vite' : r >= 1.1 ? 'Un peu plus vite' : 'Pas plus vite';
  expect(await page.locator('[data-pari="fils"] [data-juste]').textContent()).toBe(verdict);
  const question = await texteExact(page.locator('[data-pari="fils"] .q'));
  expect(question).toContain(typographier(questionFils(PROCESSEUR)));
  expect(question).toContain(`Avec ${PROCESSEUR.fils_max} fils au lieu de ${PROCESSEUR.fils_par_defaut}`);
  // La petite matrice : le meilleur chrono du processeur à 64, tous fils confondus, contre celui de la carte ;
  // « autant » sous 10 % d'écart.
  const meilleurP = Math.min(...PROCESSEUR.mesures.filter((x) => x.taille === 64).map((x) => x.millisecondes));
  const surLaCarte = ms(CARTE, 64, null);
  const petite =
    Math.max(meilleurP, surLaCarte) / Math.min(meilleurP, surLaCarte) < 1.1
      ? "Autant l'un que l'autre"
      : meilleurP < surLaCarte
        ? 'Le processeur'
        : 'La carte';
  expect(await page.locator('[data-pari="petite"] [data-juste]').textContent()).toBe(typographier(petite));
  expect(await texteExact(page.locator('[data-pari="petite"] .q'))).toContain(questionPetite());
  // La carte ne gagne pas au plus petit produit : c'est ce que l'acquis « petite » retient.
  expect(petite).not.toBe('La carte');
});

test('l’atelier suit formeDiffusee et formeProduit, réglé au clavier', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="diffusion"] [data-juste]').click();
  await expect(page.locator('[data-verrou="formes"]')).toHaveCSS('opacity', '1');

  const REGLAGES: [number[], number[], Operation][] = [
    [[3, 1], [4], 'plus'], // le départ : deux dimensions s'étirent
    [[3, 1], [4], 'produit'], // impossible : 1 colonne contre 4 lignes
    [[3, 4], [4], 'produit'], // B, un vecteur
    [[3, 2], [4, 2], 'plus'], // impossible : 3 et 4
    [[2, 3], [3, 5], 'produit'], // deux matrices
    [[2, 1, 3], [4, 1], 'plus'], // l'exercice du notebook : (2, 4, 3)
    [[2, 3, 4], [4, 5], 'produit'], // A a un lot, B n'en a pas
    [[2, 3, 4], [3, 4, 5], 'produit'], // des lots qui ne se diffusent pas
    [[1, 3, 4], [2, 4, 5], 'produit'], // le défi : deux formes à 3 dimensions
    [[6, 6, 6], [6, 6, 6], 'plus'], // les plus grandes formes
    [[1, 1, 1], [1], 'plus'], // que des 1
    [[3], [3], 'produit'], // deux vecteurs : un nombre seul, ()
  ];
  for (const [a, b, op] of REGLAGES) {
    await reglerFormes(page, a, b, op);
    const nom = `${ecrireForme(a)} ${op === 'plus' ? '+' : '@'} ${ecrireForme(b)}`;
    // La phrase des formes, écrite comme Python ; le résultat et l'explication.
    const phrase = sansBlancsDeBalisage(await texteExact(page.locator('[data-test="formes-phrase"]')));
    expect(phrase, nom).toBe(`A a la forme ${ecrireForme(a)}${FINE}; B a la forme ${ecrireForme(b)}.`);
    expect(await texteExact(page.locator('[data-test="formes-resultat"]')), nom).toBe(resultatAttendu(a, b, op));
    const explication = await texteExact(page.locator('[data-test="formes-explication"]'));
    expect(explication, nom).toBe(expliquer(a, b, op));
    if (resultatAttendu(a, b, op) === 'impossible') expect(explication, nom).toMatch(/PyTorch refuse\.$|il en faut autant\.$/);
    // La grille : les tailles de A et de B, alignées par la droite.
    const grille = page.locator('[data-test="formes-grille"]');
    const lire = (rangee: string) =>
      grille.locator(`[data-rangee="${rangee}"] td`).evaluateAll((cases) => cases.map((c) => c.querySelector('.taille')?.textContent ?? ''));
    const reel = (f: number[]) => [...new Array<string>(3 - f.length).fill(''), ...f.map(String)];
    if (op === 'produit') {
      expect(await lire('a'), nom).toEqual(reel(a));
      expect(await lire('b'), nom).toEqual(reel(b));
      // Les deux tailles qui doivent être égales sont soulignées : la dernière de A, l'avant-dernière de B.
      await expect(grille.locator('[data-souligne="oui"]'), nom).toHaveCount(2);
      await expect(grille.locator('[data-rangee="a"] td').nth(2), nom).toHaveAttribute('data-souligne', 'oui');
      await expect(grille.locator('[data-rangee="b"] td').nth(b.length === 1 ? 2 : 1), nom).toHaveAttribute('data-souligne', 'oui');
      // Égales ou non, les deux tailles soulignées le disent aussi en mots (pas seulement par la couleur),
      // et deux tailles différentes sont encadrées, comme les conflits de A + B.
      const egales = a[a.length - 1] === (b.length === 1 ? b[0] : b[b.length - 2]);
      for (const souligne of await grille.locator('[data-souligne="oui"]').all()) {
        expect(await texteExact(souligne), nom).toContain(egales ? 'égale à l’autre taille soulignée' : 'différente de l’autre taille soulignée');
        if (egales) await expect(souligne, nom).not.toHaveAttribute('data-conflit', 'oui');
        else await expect(souligne.locator('.taille'), nom).toHaveCSS('border-top-color', CORAIL);
      }
      // Un nombre seul s'écrit (), dans la rangée du résultat aussi.
      if (resultatAttendu(a, b, op) === '()') {
        expect(await texteExact(grille.locator('[data-rangee="resultat"] td')), nom).toBe('()');
      }
    } else {
      // Les cases étirées : celles que la règle de la diffusion fait grandir, et elles seules.
      const etirees = await grille.locator('[data-etire="oui"]').evaluateAll((cases) =>
        cases.map((c) => `${c.closest('tr')?.getAttribute('data-rangee')}${c.getAttribute('data-colonne')}`).sort(),
      );
      expect(etirees, nom).toEqual(etireesAttendues(a, b));
      await expect(grille.locator('[data-souligne]'), nom).toHaveCount(0);
    }
  }
  // Le dernier réglage du défi a été passé : deux formes à 3 dimensions qui se multiplient.
  await reglerFormes(page, [1, 3, 4], [2, 4, 5], 'produit');
  await expect(page.locator('[data-test="formes-defi"]')).toHaveText(DEFI_FORMES_REUSSI);
  expect(await page.locator('[data-atelier="formes"]').innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
});

test('réglages extrêmes : rien ne déborde, et le recalcul tient en moins de 200 ms', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="diffusion"] [data-juste]').click();
  await expect(page.locator('[data-verrou="formes"]')).toHaveCSS('opacity', '1');
  await reglerFormes(page, [6, 6, 6], [6, 6, 6], 'produit');
  await expect(page.locator('[data-test="formes-resultat"]')).toHaveText('(6, 6, 6)');
  await verifierSansDebordement(page);
  const taille = page.locator('[data-test="formes-b-1"]');
  const duree = await taille.evaluate(async (element) => {
    const debut = performance.now();
    element.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft', bubbles: true }));
    // Svelte met la page à jour avant la prochaine image.
    await new Promise((fin) => requestAnimationFrame(() => fin(null)));
    return performance.now() - debut;
  });
  expect(duree, `recalcul en ${Math.round(duree)} ms`).toBeLessThan(200);
  await expect(page.locator('[data-test="formes-resultat"]')).toHaveText('impossible');
  await reglerFormes(page, [1, 1, 1], [1, 1, 1], 'plus');
  await expect(page.locator('[data-test="formes-resultat"]')).toHaveText('(1, 1, 1)');
  await verifierSansDebordement(page);
});

test('le tableau des chronos est celui des fichiers de mesures', async ({ page }) => {
  await page.goto(PAGE);
  const tableau = page.locator('[data-test="chronos"]');
  const d = PROCESSEUR.fils_par_defaut;
  const m = PROCESSEUR.fils_max;
  // Les colonnes du processeur : 1 fil, le réglage par défaut, tous les fils (lus dans le fichier).
  const fils = [...new Set([1, d, m])];
  const entetes = await tableau.locator('thead th').evaluateAll((th) => th.map((e) => e.textContent ?? ''));
  expect(entetes).toEqual([
    'Taille',
    'Processeur',
    'Carte',
    ...fils.map((f) => typographier(`${f} fil${f > 1 ? 's' : ''}${f === d ? ' (réglage par défaut)' : ''}`)),
  ]);
  // Une ligne par taille mesurée : la taille, puis les durées, à trois chiffres significatifs.
  const tailles = [...new Set(PROCESSEUR.mesures.map((x) => x.taille))];
  const lignes = tableau.locator('tbody tr');
  await expect(lignes).toHaveCount(tailles.length);
  for (const [i, t] of tailles.entries()) {
    const cellules = await lignes.nth(i).locator('th, td').evaluateAll((c) => c.map((e) => e.textContent ?? ''));
    const carte = ecrireMillisecondes(ms(CARTE, t, null));
    expect(cellules, `${t}`).toEqual([`${nombre(t)} × ${nombre(t)}`, ...fils.map((f) => ecrireMillisecondes(ms(PROCESSEUR, t, f))), carte]);
  }
  // La carte a été mesurée à la porte : plus aucune valeur « à mesurer » dans le chapitre.
  await expect(page.locator('[data-a-mesurer]')).toHaveCount(0);
  await expect(tableau.locator('.a-mesurer')).toHaveCount(0);
  // La légende : les appareils, la version de PyTorch et la date du relevé, lus dans les fichiers.
  const legende = await texteExact(page.locator('[data-test="chronos-legende"]'));
  for (const m of [PROCESSEUR, CARTE]) {
    expect(legende, m.appareil).toContain(m.nom);
    expect(legende, m.appareil).toContain(`PyTorch ${m.torch}, relevé le ${formaterDate(m.releve_le)}`);
  }
  expect(legende).not.toContain('à mesurer');
  // Pas d'espace vide au-dessus du tableau (ronde 1) : le premier mot de la légende suit de près le paragraphe d'avant.
  const ecart = await page.locator('.tableau-chronos').evaluate((figure) => {
    const marcheur = document.createTreeWalker(figure.querySelector('figcaption')!, NodeFilter.SHOW_TEXT);
    let texte = marcheur.nextNode();
    while (texte && (texte.textContent ?? '').trim() === '') texte = marcheur.nextNode();
    const plage = document.createRange();
    plage.selectNodeContents(texte!);
    return plage.getClientRects()[0].top - figure.previousElementSibling!.getBoundingClientRect().bottom;
  });
  expect(ecart, `écart de ${Math.round(ecart)} px au-dessus de la légende`).toBeLessThan(60);
  // Le tableau défile dans sa zone, sans faire déborder la page ; sur un téléphone, une phrase le dit.
  const zone = page.locator('[data-test="chronos-zone"]');
  await expect(zone).toHaveCSS('overflow-x', 'auto');
  const indice = page.locator('[data-test="chronos-indice"]');
  if ((page.viewportSize()?.width ?? 0) <= 600) await expect(indice).toBeVisible();
  else await expect(indice).toBeHidden();
  await verifierSansDebordement(page);
});

test('le code affiché est celui des régions testées', async ({ page }) => {
  await page.goto(PAGE);
  const blocs = page.locator('.code-explique');
  await expect(blocs).toHaveCount(REGIONS.length);
  for (const [i, [fichier, region]] of REGIONS.entries()) {
    const attendu = extraireRegion(readFileSync(`../${fichier}`, 'utf8'), region, fichier);
    // Chaque région finit sur sa dernière ligne de code : aucune ligne vide numérotée sous l'extrait.
    expect(attendu.endsWith('\n'), `${region} finit par une ligne vide`).toBe(false);
    expect(await blocs.nth(i).locator('pre').evaluate((pre) => pre.textContent), region).toBe(attendu);
    await expect(blocs.nth(i).locator('figcaption a')).toHaveAttribute('href', `https://github.com/chipat-neko/forge-ia/blob/main/${fichier}`);
  }
  await expect(page.getByRole('link', { name: 'Le projet complet' })).toHaveAttribute(
    'href',
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/0.4-tenseurs',
  );
  await expect(page.getByRole('link', { name: 'Ouvrir dans Colab' })).toHaveAttribute(
    'href',
    'https://colab.research.google.com/github/chipat-neko/forge-ia/blob/main/notebooks/0.4-tenseurs.ipynb',
  );
});

test('les commandes affichées sont celles de commandes.ts', async ({ page }) => {
  await page.goto(PAGE);
  const blocs = await page
    .locator('.bloc-commande pre code')
    .evaluateAll((codes) => codes.map((c) => (c.textContent ?? '').split('\n')));
  expect(blocs).toEqual(COMMANDES_DES_BLOCS);
  // Les commandes citées dans le texte et dans les notes viennent aussi de commandes.ts.
  const connues = new Set(Object.values(commandes));
  const citees = await page.locator('.etape p code').allTextContents();
  for (const code of citees) {
    if (/^(uv (sync|run) |pip |git |cd |\$env:|export )/.test(code)) expect(connues, code).toContain(code);
  }
  // Pour forcer le processeur, les deux formes de la variable FORGE_APPAREIL, celles du chapitre 0.3.
  for (const commande of [commandes.FORCER_PROCESSEUR_POWERSHELL, commandes.FORCER_PROCESSEUR_BASH]) {
    expect(citees, commande).toContain(commande);
  }
});

test('l’ouverture, les exemples, la mémoire et l’encadré viennent des données', async ({ page }) => {
  await page.goto(PAGE);
  // L'ouverture : le tenseur qui entre dans ton IA, dans sa plus grande taille.
  const { contexte, dim, parametres } = PRESETS_FORGE.tres_grand;
  expect(await texteExact(page.locator('[data-test="ouverture-forme"]'))).toBe(`(micro-lot, ${nombre(contexte)}, ${nombre(dim)})`);
  expect(await texteExact(page.locator('[data-test="ouverture"]'))).toContain(`${nombre(contexte)} × ${nombre(dim)} = ${nombre(contexte * dim)}`);
  // Les formes de l'étape 1 sont celles des exemples du projet, écrites comme Python : (4,) pour un vecteur.
  const etape1 = await texteExact(page.locator('#etape-1 .texte'));
  for (const nom of ['vecteur', 'matrice', 'lot']) expect(etape1, nom).toContain(ecrireForme(ATTENDUS.exemples.creer[nom].forme));
  expect(etape1).toContain('(4,)');
  // Étape 5 : 1 Mo = 2²⁰ octets, et les poids de ton IA en bf16, par le calculateur.
  // La taille de la version pour la carte (étape 6) : une taille de téléchargement, en Go décimaux comme
  // PyPI et le chapitre 0.3 (« 2,1 Go »), et non en Go de 2³⁰ octets comme la mémoire des tenseurs.
  expect(await texteExact(page.locator('#etape-6'))).toContain(enGo(OCTETS_ROUE_CU132_WINDOWS));
  const etape5 = await texteExact(page.locator('#etape-5'));
  expect(etape5).toContain(nombre(2 ** 20));
  // Les poids de ton IA restent en float32 (autocast calcule en bf16) : les deux tailles, calculées.
  expect(etape5).toContain(formaterOctets(memoirePoidsOctets(parametres, 4)));
  expect(etape5).toContain(formaterOctets(memoirePoidsOctets(parametres, 2)));
  expect(etape5).toContain('restent en float32');
  // Le pic de mémoire mesuré pour un micro-lot d'un seul texte, cité aux étapes 1 et 5, avec le rapport de mesure.
  const pic = `${nombre(MESURES_TON_IA.tres_grand.carte.memoireGo, 1)}\u00A0Go`;
  expect(MESURES_TON_IA.tres_grand.carte.microLot).toBe(1);
  expect(await texteExact(page.locator('#etape-1 .note'))).toContain(pic);
  expect(await texteExact(page.locator('#etape-1 .note'))).toContain('deux ne tiennent pas dans sa mémoire');
  await expect(page.locator(`#etape-1 .note a[href="${MESURES_TON_IA.tres_grand.source.url}"]`)).toHaveCount(1);
  expect(etape5).toContain(pic);
  // Étape 7 : l'explication du pari « fils » est celle que tirent les mesures (phraseFils).
  expect(await texteExact(page.locator('[data-pari="fils"] .explication'))).toContain(phraseFils(PROCESSEUR));
  // Étape 6 : le pari « petite », avant le tableau (qui donnerait la réponse), puis ce que montrent les chronos,
  // puis le prix du transfert ; chaque phrase est celle que tirent les deux fichiers de mesures.
  const etape6 = page.locator('#etape-6');
  expect(await texteExact(etape6.locator('[data-pari="petite"] .explication'))).toContain(explicationPetite(PROCESSEUR, CARTE));
  expect(await texteExact(etape6.locator('[data-test="chronos-phrase"]'))).toBe(phraseCarteEtProcesseur(PROCESSEUR, CARTE));
  expect(await texteExact(etape6.locator('[data-test="transfert-phrase"]'))).toBe(phraseTransfert(CARTE));
  const ordre = await etape6.evaluate((etape) =>
    [...etape.querySelectorAll('[data-pari="petite"], [data-test="chronos"], [data-test="chronos-phrase"], [data-test="transfert-phrase"]')].map(
      (e) => e.getAttribute('data-pari') ?? e.getAttribute('data-test'),
    ),
  );
  expect(ordre).toEqual(['petite', 'chronos', 'chronos-phrase', 'transfert-phrase']);
  // L'encadré : la crête d'une H100 en bf16, et les efficacités de PaLM et de Llama 3, sourcées.
  const labo = page.locator('#etape-8 .labo');
  const texteLabo = await texteExact(labo);
  const h100 = materiel('h100-sxm');
  expect(texteLabo).toContain(nombre(h100.creteTflops));
  const liens = await labo.locator('a').evaluateAll((a) => a.map((e) => e.getAttribute('href')));
  expect(liens).toContain(h100.source.url);
  for (const r of REPERES_EFFICACITE) {
    expect(liens, r.modele).toContain(r.source.url);
    expect(texteLabo, r.modele).toContain(r.min === r.max ? pourcent(r.min, 1) : `${pourcent(r.min, 0).replace(`${FINE}%`, '')} à ${pourcent(r.max, 0)}`);
  }
  // Aucune version de Colab ni de PyTorch dans le texte, sauf celles des fichiers de mesures, dans la légende des chronos.
  const texte = (await texteExact(page.locator('main'))).replaceAll(PROCESSEUR.torch, '').replaceAll(CARTE.torch, '');
  expect(texte).not.toMatch(/\b2\.\d+\.\d+/);
});

test('sans JavaScript, l’atelier montre (3, 1) + (4,) = (3, 4), et tout se lit', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  await expect(page.locator('[data-test="ouverture"]')).toBeVisible();
  // Pas de verrou : l'atelier est là, net, avec ses formes de départ.
  await expect(page.locator('[data-verrou="formes"]')).not.toHaveAttribute('inert', '');
  const phrase = sansBlancsDeBalisage(await texteExact(page.locator('[data-test="formes-phrase"]')));
  expect(phrase).toBe(`A a la forme ${ecrireForme(A_DEPART)}${FINE}; B a la forme ${ecrireForme(B_DEPART)}.`);
  await expect(page.locator('[data-test="formes-op-plus"]')).toHaveAttribute('aria-pressed', 'true');
  expect(await texteExact(page.locator('[data-test="formes-resultat"]'))).toBe('(3, 4)');
  expect(await texteExact(page.locator('[data-test="formes-explication"]'))).toBe(expliquer(A_DEPART, B_DEPART, 'plus'));
  await expect(page.locator('[data-test="formes-grille"]')).toBeVisible();
  // Les explications des quatre paris sont données d'emblée ; le tableau des chronos et ses phrases sont là.
  for (const id of PARIS) await expect(page.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  await expect(page.locator('[data-test="chronos"]')).toBeVisible();
  await expect(page.locator('[data-test="chronos-phrase"]')).toBeVisible();
  await expect(page.locator('[data-test="transfert-phrase"]')).toBeVisible();
  await expect(page.locator('#etape-8 .labo')).toBeVisible();
  await verifierSansDebordement(page);
  await ctx.close();
});
