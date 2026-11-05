// Parcours du chapitre 0.5, « Premier réseau de neurones » : un brouillon
// (src/brouillons/chapitres/0-5.mdx) tant qu'il n'a pas paru, construit à son
// adresse définitive avec FORGE_ESSAIS=1.
//
// Les attendus viennent du jumeau du neurone (neurone.ts), de l'atelier
// (atelier-neurone.ts), des paris (paris-0-5.ts), des commandes (commandes.ts),
// des données du calculateur, et des fichiers du projet, lus sur le disque par
// readFileSync : projets/0.5-reseau/tests/attendus.json et sorties/*.txt. Ces
// modules sont purs : un parcours, chargé par Node sans Vite, peut les importer
// (B1). Ni etatInitial (le moteur du mini-modèle lit ses prénoms par ?raw), ni
// aucun module à ?raw, .json ou astro:*.
//
// Les prénoms du mini-modèle au départ (ouverture, étape 9, avant-goût) se
// comparent donc à la même page sans JavaScript, qu'Astro a construite avec
// etatInitial ; apercu.test.ts vérifie, lui, l'égalité avec etatInitial.
import { existsSync, readFileSync } from 'node:fs';
import { test, expect, type Locator, type Page } from '@playwright/test';
import { modelePublic } from '../src/lib/calculateur/donnees';
import { formaterDate, formaterQuantite } from '../src/lib/calculateur/formats';
import { PRESETS_FORGE } from '../src/lib/calculateur/ton-ia';
import { PRESETS_MINI } from '../src/lib/mini-modele/reglages';
import { nombre } from '../src/lib/nombres';
import { titreCourt, trouverChapitre } from '../src/lib/parcours';
import { extraireRegion } from '../src/lib/regions';
import { lireSortie } from '../src/lib/sorties';
import { enGo, OCTETS_ROUE_CU132_WINDOWS } from '../src/lib/partie-0/sources-0-3';
import { typographier } from '../src/lib/typo';
import { bilan, DEFI_NEURONE_REUSSI, SANS_POIDS } from '../src/lib/partie-0/atelier-neurone';
import * as commandes from '../src/lib/partie-0/commandes';
import { bienClasses, meilleurReglage, POINTS, PORTES, sortieSeuil, type Porte } from '../src/lib/partie-0/neurone';
import {
  choixCoince,
  choixExact,
  choixGradientSortie,
  choixXor,
  dureeDeLaSortie,
  ecartsDeLaSortie,
  ecrireValeur,
  etiquetteCourbe,
  lignesPredictions,
  phraseDurees,
  type AttenduGraine,
  type AttendusEntrainement,
} from '../src/lib/partie-0/paris-0-5';
import {
  attendreHydratation,
  colonneAvantApres,
  plusLongueLigne,
  verifierAxe,
  verifierDroiteEnTirets,
  verifierLiensVersParus,
  verifierSansDebordement,
  verifierStructureAvantApres,
  verifierTypographieHorsCode,
} from './outils';

const PAGE = '/forge-ia/partie-0/0-5/';
const FINE = '\u202F';
const MOINS = '−';

// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
const ATTENDUS = JSON.parse(readFileSync('../projets/0.5-reseau/tests/attendus.json', 'utf8')) as {
  entrainement: AttendusEntrainement;
  graines: AttenduGraine[];
};
const E = ATTENDUS.entrainement;
const FICHIER_PROCESSEUR = 'projets/0.5-reseau/sorties/processeur.txt';
const FICHIER_CARTE = 'projets/0.5-reseau/sorties/rtx-5070-ti.txt';
const SORTIE_PROCESSEUR = readFileSync(`../${FICHIER_PROCESSEUR}`, 'utf8');
// La sortie de la carte, relevée à la porte de la Partie 0, carte au repos : le chapitre n'a plus rien « à mesurer ».
const SORTIE_CARTE = readFileSync(`../${FICHIER_CARTE}`, 'utf8');
const AVANT_GOUT = PRESETS_MINI['avant-gout'];

/** Les titres des dix étapes, dans l'ordre. */
const TITRES = [
  'Un neurone',
  'Le OU exclusif',
  'Deux couches',
  'L’erreur',
  'Remonter l’erreur',
  'Entraîner à la main',
  'Le même, avec PyTorch',
  'Sur la carte',
  'La même boucle, en plus grand',
  'À grande échelle',
];
const PARIS = ['xor', 'gradient', 'exact', 'coince'];
/** Les acquis, dans l'ordre du chapitre, avec leur texte du brief. */
const ACQUIS: [string, string][] = [
  ['neurone', 'Un neurone fait une somme pondérée, puis décide.'],
  ['xor', 'Un seul neurone ne sait pas tout séparer : il faut une couche de plus.'],
  ['gradient', "L'erreur remonte couche par couche, par la règle de la chaîne."],
  ['entraine', "Entraîner, c'est répéter : propager, mesurer l'erreur, remonter, corriger."],
  ['coince', 'Selon son départ, un réseau peut rester coincé.'],
  ['avant-gout', 'La même boucle fait apprendre un vrai petit modèle.'],
];
const NB_ACQUIS = ACQUIS.length;

/** Les commandes que les blocs « À taper » du chapitre montrent, dans l'ordre de la page. */
const COMMANDES_DES_BLOCS = [
  // Le dépôt déjà téléchargé au chapitre 0.1 se met à jour ; sinon, on le télécharge.
  [commandes.METTRE_A_JOUR_DEPOT, commandes.ALLER_AU_PROJET_0_5],
  [commandes.CLONER_DEPOT, commandes.ALLER_AU_PROJET_0_5],
  [commandes.RESEAU_ENTRAINER_CPU],
  [commandes.RESEAU_ENTRAINER_GPU],
];

/** Les régions de code montrées, dans l'ordre de la page. */
const REGIONS: [string, string][] = [
  ['projets/0.5-reseau/premier_reseau/neurone.py', 'neurone'],
  ['projets/0.5-reseau/premier_reseau/a_la_main.py', 'sigmoide'],
  ['projets/0.5-reseau/premier_reseau/a_la_main.py', 'propager'],
  ['projets/0.5-reseau/premier_reseau/a_la_main.py', 'erreur'],
  ['projets/0.5-reseau/premier_reseau/a_la_main.py', 'retropropager'],
  ['projets/0.5-reseau/premier_reseau/a_la_main.py', 'pas'],
  ['projets/0.5-reseau/premier_reseau/a_la_main.py', 'entrainer'],
  ['projets/0.5-reseau/premier_reseau/avec_pytorch.py', 'modele'],
  ['projets/0.5-reseau/premier_reseau/avec_pytorch.py', 'autograd'],
  ['projets/0.5-reseau/premier_reseau/avec_pytorch.py', 'entrainer-pytorch'],
];

/** Le texte exact d'un élément (textContent : toHaveText ramènerait U+202F à une espace ordinaire). */
async function texteExact(zone: Locator): Promise<string> {
  return (await zone.textContent()) ?? '';
}

/** Attend la fin des animations en cours (verdict des paris, coches) : axe mesure alors les vraies couleurs. */
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

/** Règle un nombre jaune au clavier sur une valeur (aria-valuenow), par les flèches, de 0,5 en 0,5. */
async function regler(nombre: Locator, valeur: number): Promise<void> {
  await nombre.focus();
  const actuelle = Number(await nombre.getAttribute('aria-valuenow'));
  const crans = Math.round(Math.abs(valeur - actuelle) / 0.5);
  for (let i = 0; i < crans; i++) await nombre.press(valeur > actuelle ? 'ArrowRight' : 'ArrowLeft');
  await expect(nombre).toHaveAttribute('aria-valuenow', String(valeur));
}

/** Choisit une porte au clavier. */
async function choisirPorte(page: Page, porte: Porte): Promise<void> {
  const bascule = page.locator(`[data-test="neu-porte"][data-porte="${porte}"]`);
  await bascule.focus();
  await page.keyboard.press('Enter');
  await expect(bascule).toHaveAttribute('aria-pressed', 'true');
}

/** Règle la porte, puis w1, w2 et b, au clavier. */
async function reglerNeurone(page: Page, porte: Porte, w1: number, w2: number, b: number): Promise<void> {
  await choisirPorte(page, porte);
  await regler(page.locator('[data-test="neu-w1"]'), w1);
  await regler(page.locator('[data-test="neu-w2"]'), w2);
  await regler(page.locator('[data-test="neu-b"]'), b);
}

/** Les prénoms d'une colonne du tableau de l'avant-goût, sans « (existe déjà) » ni « (aucune lettre) ». */
function prenomsSeuls(colonne: string[]): string[] {
  return colonne.map((c) => c.replace(/ \(existe déjà\)$/, '')).filter((c) => c !== '(aucune lettre)');
}

/** La colonne de gauche de l'avant-goût, telle qu'Astro l'a construite : la page sans JavaScript (B1). */
async function departSansJavaScript(page: Page, baseURL: string | undefined): Promise<string[]> {
  const ctx = await page.context().browser()!.newContext({ javaScriptEnabled: false, baseURL });
  const statique = await ctx.newPage();
  await statique.goto(PAGE);
  const colonne = await colonneAvantApres(statique.locator('[data-test="mini-avant-apres"]'), 1);
  await ctx.close();
  return colonne;
}

test('chapitre 0.5 complet, avec l’avant-goût mené jusqu’au bout', async ({ page, baseURL }) => {
  test.setTimeout(240_000);
  const reference = await departSansJavaScript(page, baseURL);
  expect(reference).toHaveLength(AVANT_GOUT.nbEchantillons);

  await page.goto(PAGE);
  await attendreHydratation(page);
  const { total } = trouverChapitre('0.5');
  await expect(page.locator('header')).toContainText(`Partie 0, chapitre 0.5 sur ${total}`);
  // Dix étapes, dans l'ordre, quatre paris et six acquis ; le programme les compte.
  const titres = page.locator('.etape h2');
  await expect(titres).toHaveCount(TITRES.length);
  expect(await titres.evaluateAll((h) => h.map((e) => e.textContent))).toEqual(TITRES.map(typographier));
  expect(await texteExact(page.locator('.programme'))).toContain(`${TITRES.length} étapes, ${PARIS.length} paris`);
  await expect(page.locator('[data-pari]')).toHaveCount(PARIS.length);
  await expect(page.locator('#recap [data-acquis]')).toHaveCount(NB_ACQUIS);
  for (const [cle, texte] of ACQUIS) {
    expect(await texteExact(page.locator(`#recap [data-acquis="${cle}"]`)), cle).toContain(typographier(texte));
  }

  // L'atelier, sans verrou : sur ET, b réglé à −1,5 classe les 4 points, et gagne l'acquis du neurone.
  await expect(page.locator('[data-test="neu-w1"]')).not.toHaveAttribute('aria-disabled', 'true');
  await regler(page.locator('[data-test="neu-b"]'), -1.5);
  await expect(page.locator('[data-test="neu-bilan"]')).toHaveText('Les 4 points sont bien classés.');
  await expect(page.locator('#recap [data-acquis="neurone"]')).toHaveAttribute('data-gagne', 'oui');

  // Les quatre paris.
  for (const id of PARIS) await page.locator(`[data-pari="${id}"] [data-juste]`).click();
  await expect(page.locator('#recap [data-gagne="oui"]')).toHaveCount(1 + PARIS.length);

  // L'avant-goût : le tableau, sa colonne de gauche égale à la page sans JavaScript, puis 600 pas jusqu'au bout.
  const demo = page.locator('[data-mini="avant-gout"]');
  const tableau = demo.locator('[data-test="mini-avant-apres"]');
  await verifierStructureAvantApres(tableau, AVANT_GOUT.nbEchantillons);
  expect(await colonneAvantApres(tableau, 1)).toEqual(reference);
  await verifierDroiteEnTirets(tableau, AVANT_GOUT.nbEchantillons);
  await demo.locator('[data-test="mini-action"]').click();
  await expect(demo).toHaveAttribute('data-phase', 'termine', { timeout: 120_000 });
  await expect(demo.locator('[data-test="mini-etat"]')).toHaveAttribute('data-pas', String(AVANT_GOUT.pasTotal));
  expect(await colonneAvantApres(tableau, 1)).toEqual(reference);
  const droite = await colonneAvantApres(tableau, 2);
  expect(droite).toHaveLength(AVANT_GOUT.nbEchantillons);
  for (const prenom of droite) expect(prenom).toMatch(/^[^\s—]/);
  await expect(page.locator('#recap [data-acquis="avant-gout"]')).toHaveAttribute('data-gagne', 'oui');
  await expect(page.locator('#recap [data-total]')).toContainText(`${NB_ACQUIS} sur ${NB_ACQUIS}`);

  // Le pied suit les fichiers : 0.4 et 1.1 sont « à venir » tant qu'ils n'ont pas paru (S2).
  await verifierVoisin(page, 'precedent', '0-4.mdx', '/forge-ia/partie-0/0-4/');
  await verifierVoisin(page, 'suivant', '1-1.mdx', '/forge-ia/partie-1/1-1/');
  // Aucun lien vers un chapitre qui n'a pas paru (S3) : les renvois à 0.3, 0.4, 1.1 et 1.5 sont du texte.
  await verifierLiensVersParus(page.locator('main'), PAGE);

  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'));
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
  expect(await page.locator('main').innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
});

test('les choix des paris viennent du jumeau du neurone et des attendus', async ({ page }) => {
  await page.goto(PAGE);
  const attendus: Record<string, { texte: string; juste?: boolean }[]> = {
    xor: choixXor(),
    gradient: choixGradientSortie(),
    exact: choixExact(E),
    coince: choixCoince(ATTENDUS.graines),
  };
  for (const id of PARIS) {
    const boutons = page.locator(`[data-pari="${id}"] button[data-choix]`);
    expect(await boutons.allTextContents(), id).toEqual(attendus[id].map((c) => typographier(c.texte)));
    const juste = attendus[id].find((c) => c.juste)!;
    expect(await page.locator(`[data-pari="${id}"] [data-juste]`).textContent(), id).toBe(typographier(juste.texte));
  }
  // Les bonnes réponses, recalculées ici depuis le jumeau et le fichier.
  const meilleur = meilleurReglage('ou_exclusif')[0];
  expect(await page.locator('[data-pari="xor"] [data-juste]').textContent()).toBe(`Non${FINE}: au mieux ${meilleur} points sur ${POINTS.length}`);
  expect(await page.locator('[data-pari="gradient"] [data-juste]').textContent()).toBe('0,9');
  const bornes = [Math.min(...E.predictions), Math.max(...E.predictions)].map(ecrireValeur);
  expect(await page.locator('[data-pari="exact"] [data-juste]').textContent()).toBe(`Non${FINE}: il s’en approche, de ${bornes[0]} à ${bornes[1]}`);
  const coinces = ATTENDUS.graines.filter((g) => !g.reussit).length;
  expect(await page.locator('[data-pari="coince"] [data-juste]').textContent()).toBe(`${coinces} fois`);
  expect(await texteExact(page.locator('[data-pari="coince"] .q'))).toContain(`Sur ${ATTENDUS.graines.length} départs au hasard`);
  expect(await texteExact(page.locator('[data-pari="exact"] .q'))).toContain(`Après ${nombre(E.nb_pas)} pas`);
});

test('l’atelier suit bienClasses, réglé au clavier, poids nuls compris', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  const REGLAGES: [Porte, number, number, number][] = [
    ['et', 1, 1, 0], // le départ : 2 points sur 4
    ['et', 1, 1, -1.5], // les 4 points
    ['ou', 1, 1, -1.5], // le même réglage, sur OU
    ['ou', 1, 1, -0.5], // OU : même poids, autre b
    ['ou_exclusif', 1, 1, -0.5], // le OU exclusif : 3 au mieux
    ['ou_exclusif', -2, 0.5, 0], // le meilleur réglage de la grille
    ['et', 0, 0, 0], // sans poids : 0 partout
    ['et', 0, 0, 1], // sans poids : 1 partout
    ['et', -1, -1, 1.5], // aucun point
    ['et', 2, 0, 2], // la droite passe hors du dessin
    ['ou', 2, 2, -2], // les bords de la grille
  ];
  for (const [porte, w1, w2, b] of REGLAGES) {
    await reglerNeurone(page, porte, w1, w2, b);
    const nom = `${porte} ${w1} ${w2} ${b}`;
    // Le bilan, recalculé point par point avec sortieSeuil.
    const reponses = POINTS.map((x) => sortieSeuil([w1, w2], b, x));
    const justes = reponses.map((r, i) => r === PORTES[porte][i]);
    expect(justes.filter(Boolean).length, nom).toBe(bienClasses([w1, w2], b, porte));
    expect(await texteExact(page.locator('[data-test="neu-bilan"]')), nom).toBe(bilan(justes.filter(Boolean).length));
    // Chaque point, dans le texte et dans le dessin : bien ou mal classé.
    const lignes = page.locator('[data-test="neu-points"] li');
    await expect(lignes, nom).toHaveCount(POINTS.length);
    const marques = page.locator('[data-test="neu-dessin"] [data-test="neu-marque"]');
    await expect(marques, nom).toHaveCount(POINTS.length);
    for (const [i, x] of POINTS.entries()) {
      const etat = justes[i] ? 'oui' : 'non';
      await expect(lignes.nth(i), nom).toHaveAttribute('data-juste', etat);
      await expect(marques.nth(i), nom).toHaveAttribute('data-juste', etat);
      const somme = (w1 * x[0] + w2 * x[1] + b).toString().replace('.', ',').replace('-', MOINS);
      expect(await texteExact(lignes.nth(i)), nom).toContain(
        `(${x[0]}, ${x[1]})${FINE}: somme ${somme}, réponse ${reponses[i]}, il faut ${PORTES[porte][i]}, ${justes[i] ? 'bien' : 'mal'} classé.`,
      );
    }
    // La droite : absente sans poids, avec le message du brief.
    const sansPoids = w1 === 0 && w2 === 0;
    if (sansPoids) {
      await expect(page.locator('[data-test="neu-droite"]'), nom).toHaveCount(0);
      expect(await texteExact(page.locator('[data-test="neu-remarque"]')), nom).toBe(SANS_POIDS);
    } else if (w1 === 2 && w2 === 0 && b === 2) {
      await expect(page.locator('[data-test="neu-droite"]'), nom).toHaveCount(0);
      expect(await texteExact(page.locator('[data-test="neu-remarque"]')), nom).toContain('hors du dessin');
    } else {
      await expect(page.locator('[data-test="neu-droite"]'), nom).toHaveCount(1);
      await expect(page.locator('[data-test="neu-remarque"]'), nom).toHaveCount(0);
    }
    // Le OU exclusif n'est jamais classé en entier.
    if (porte === 'ou_exclusif') expect(justes.every(Boolean), nom).toBe(false);
    // Aucun NaN, ni dans le texte, ni dans les attributs du dessin.
    expect(await page.locator('[data-atelier="neurone"]').innerText(), nom).not.toMatch(/NaN|Infinity|undefined/);
    expect(await page.locator('[data-test="neu-dessin"]').innerHTML(), nom).not.toMatch(/NaN|Infinity/);
  }
  // Le défi a été passé : ET puis OU avec w1 = w2 = 1, en ne changeant que b.
  await expect(page.locator('[data-test="neu-defi"]')).toHaveText(DEFI_NEURONE_REUSSI);
  await verifierSansDebordement(page);
});

test('au clavier, b réglé à −1,5 sur ET classe les 4 points et gagne l’acquis', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await expect(page.locator('[data-test="neu-porte"][data-porte="et"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('[data-test="neu-bilan"]')).toHaveText('2 points sur 4 bien classés.');
  await expect(page.locator('#recap [data-acquis="neurone"]')).toHaveAttribute('data-gagne', 'non');
  // Le départ classe déjà OU : y passer ne gagne rien, ce n'est pas un réglage du lecteur.
  await choisirPorte(page, 'ou');
  await expect(page.locator('[data-test="neu-bilan"]')).toHaveText('Les 4 points sont bien classés.');
  await expect(page.locator('#recap [data-acquis="neurone"]')).toHaveAttribute('data-gagne', 'non');
  await choisirPorte(page, 'et');
  const b = page.locator('[data-test="neu-b"]');
  await regler(b, -1.5);
  await expect(b).toHaveAttribute('aria-valuetext', `${MOINS}1,5`);
  await expect(b).toHaveText(`${MOINS}1,5`);
  await expect(page.locator('[data-test="neu-bilan"]')).toHaveText('Les 4 points sont bien classés.');
  await expect(page.locator('#recap [data-acquis="neurone"]')).toHaveAttribute('data-gagne', 'oui');
});

test('réglages extrêmes : rien ne déborde, et le recalcul tient en moins de 200 ms', async ({ page }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await reglerNeurone(page, 'ou_exclusif', -2, -2, -2);
  await verifierSansDebordement(page);
  const duree = await page.locator('[data-test="neu-w1"]').evaluate(async (element) => {
    const debut = performance.now();
    element.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    await new Promise((fin) => requestAnimationFrame(() => fin(null)));
    return performance.now() - debut;
  });
  expect(duree, `recalcul en ${Math.round(duree)} ms`).toBeLessThan(200);
  await reglerNeurone(page, 'et', 2, 2, 2);
  await verifierSansDebordement(page);
  expect(await page.locator('[data-atelier="neurone"]').innerText()).not.toMatch(/NaN|Infinity|undefined/);
});

test('la courbe : un aria-label aux valeurs des attendus, aucun NaN', async ({ page }) => {
  await page.goto(PAGE);
  const courbe = page.locator('[data-test="courbe-xor"]');
  await expect(courbe).toHaveCount(1);
  await expect(courbe).toHaveAttribute('role', 'img');
  await expect(courbe).toHaveAttribute('viewBox', '0 0 640 240');
  const etiquette = await courbe.getAttribute('aria-label');
  expect(etiquette).toBe(etiquetteCourbe(E.pertes));
  expect(etiquette).toBe(
    `Erreur du réseau${FINE}: ${ecrireValeur(E.pertes[0])} au pas 0, ${ecrireValeur(E.pertes[E.pertes.length - 1])} au pas ${nombre(E.nb_pas)}.`,
  );
  const d = await courbe.locator('path').first().getAttribute('d');
  expect(d).toMatch(/^M/);
  expect(await courbe.evaluate((svg) => svg.outerHTML)).not.toMatch(/NaN|Infinity/);
  // Les axes, en Gabarito 13 px et encre douce.
  const figure = page.locator('[data-test="courbe-xor-figure"]');
  for (const axe of ['pas', 'erreur']) {
    const titre = figure.locator(`[data-axe="${axe}"]`);
    await expect(titre).toHaveText(axe);
    await expect(titre).toHaveCSS('font-size', '13px');
    expect(await titre.evaluate((e) => getComputedStyle(e).fontFamily)).toContain('Gabarito');
  }
  await verifierSansDebordement(page);
});

test('le tableau des prédictions est celui des attendus', async ({ page }) => {
  await page.goto(PAGE);
  const tableau = page.locator('[data-test="predictions"]');
  const lignes = tableau.locator('tbody tr');
  await expect(lignes).toHaveCount(POINTS.length);
  const attendues = lignesPredictions(E);
  for (const [i, ligne] of attendues.entries()) {
    const cellules = await lignes.nth(i).locator('th, td').evaluateAll((c) => c.map((e) => e.textContent ?? ''));
    expect(cellules, `ligne ${i}`).toEqual(ligne);
    // Recalculé ici : la réponse du fichier à 3 décimales, et son arrondi égal à la bonne réponse.
    expect(cellules[2]).toBe(nombre(E.predictions[i], 3));
    expect(Number(cellules[3])).toBe(PORTES.ou_exclusif[i]);
  }
});

test('les sorties : celles du processeur et de la carte sont les fichiers, et la phrase des durées en vient', async ({ page }) => {
  await page.goto(PAGE);
  // Les deux sorties, telles que le script les a enregistrées : contenu, date du relevé, commande.
  for (const [fichier, texte, commande] of [
    [FICHIER_PROCESSEUR, SORTIE_PROCESSEUR, commandes.RESEAU_ENTRAINER_CPU],
    [FICHIER_CARTE, SORTIE_CARTE, commandes.RESEAU_ENTRAINER_GPU],
  ]) {
    const sortie = page.locator(`[data-sortie="${fichier}"]`);
    await expect(sortie, fichier).toHaveCount(1);
    const lue = lireSortie(texte, fichier)!;
    expect(await texteExact(sortie.locator('[data-contenu]')), fichier).toBe(lue.contenu);
    expect(await texteExact(sortie.locator('figcaption')), fichier).toContain(`relevée le ${formaterDate(lue.releveLe!)}`);
    await expect(sortie.locator('.commande'), fichier).toHaveText(commande);
  }
  // La sortie de la carte est à l'étape 8, celle du processeur à l'étape 7.
  await expect(page.locator(`#etape-7 [data-sortie="${FICHIER_PROCESSEUR}"]`)).toHaveCount(1);
  await expect(page.locator(`#etape-8 [data-sortie="${FICHIER_CARTE}"]`)).toHaveCount(1);
  // Le texte cite les deux écarts tels que la sortie du processeur les écrit.
  const { gradients, poids } = ecartsDeLaSortie(SORTIE_PROCESSEUR);
  expect(await texteExact(page.locator('#etape-7 .texte'))).toContain(gradients);
  expect(await texteExact(page.locator('#etape-7 .texte'))).toContain(poids);
  // La carte a été relevée à la porte : plus aucune valeur « à mesurer ».
  await expect(page.locator('[data-a-mesurer]')).toHaveCount(0);
  // L'étape 8 ne parle de vitesse que dans la phrase des durées, tirée des deux sorties.
  const processeur = dureeDeLaSortie(SORTIE_PROCESSEUR);
  const carte = dureeDeLaSortie(SORTIE_CARTE);
  expect([processeur.appareil, carte.appareil]).toEqual(['cpu', 'cuda']);
  const durees = page.locator('#etape-8 [data-test="durees"]');
  expect(await texteExact(durees)).toBe(phraseDurees(processeur, carte));
  expect(await texteExact(durees)).toContain(`la carte a mis ${carte.texte}\u00A0ms, et le processeur ${processeur.texte}\u00A0ms`);
  // Recalculé ici : la carte est bien la plus lente, d'au moins 10 %.
  expect(carte.millisecondes / processeur.millisecondes).toBeGreaterThanOrEqual(1.1);
  const etape8 = await texteExact(page.locator('#etape-8 .texte'));
  // La taille de la version pour la carte : en Go décimaux, comme PyPI et le chapitre 0.3 (« 2,1 Go »).
  expect(etape8).toContain(enGo(OCTETS_ROUE_CU132_WINDOWS));
  const horsPhrase = etape8.replace(await texteExact(durees), '');
  expect(horsPhrase).not.toMatch(/plus vite|plus lent|moins vite|fois plus|rapide/);
});

test('le code affiché est celui des régions testées', async ({ page }) => {
  await page.goto(PAGE);
  const blocs = page.locator('.code-explique');
  await expect(blocs).toHaveCount(REGIONS.length);
  for (const [i, [fichier, region]] of REGIONS.entries()) {
    const attendu = extraireRegion(readFileSync(`../${fichier}`, 'utf8'), region, fichier);
    expect(attendu.endsWith('\n'), `${region} finit par une ligne vide`).toBe(false);
    expect(await blocs.nth(i).locator('pre').evaluate((pre) => pre.textContent), region).toBe(attendu);
    await expect(blocs.nth(i).locator('figcaption a')).toHaveAttribute('href', `https://github.com/chipat-neko/forge-ia/blob/main/${fichier}`);
  }
  await expect(page.getByRole('link', { name: 'Le projet complet' })).toHaveAttribute(
    'href',
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/0.5-reseau',
  );
  await expect(page.getByRole('link', { name: 'Ouvrir dans Colab' })).toHaveAttribute(
    'href',
    'https://colab.research.google.com/github/chipat-neko/forge-ia/blob/main/notebooks/0.5-reseau.ipynb',
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
  for (const commande of [commandes.FORCER_PROCESSEUR_POWERSHELL, commandes.FORCER_PROCESSEUR_BASH]) {
    expect(citees, commande).toContain(commande);
  }
  // Après les invites des sorties, les mêmes commandes.
  for (const commande of await page.locator('.sortie .commande').allTextContents()) {
    expect(connues, commande).toContain(commande);
  }
});

test('l’ouverture et l’étape 9 citent les premiers prénoms du départ, et l’encadré vient des données', async ({
  page,
  baseURL,
}) => {
  const reference = prenomsSeuls(await departSansJavaScript(page, baseURL)).slice(0, 2);
  expect(reference).toHaveLength(2);
  await page.goto(PAGE);
  // L'ouverture : les deux premiers prénoms inventés au départ, ceux du tableau de l'avant-goût.
  const ouverture = page.locator('[data-test="ouverture"]');
  expect(await ouverture.locator('[data-test="ouverture-prenom"]').allTextContents()).toEqual(reference);
  expect(prenomsSeuls(await colonneAvantApres(page.locator('[data-test="mini-avant-apres"]'), 1)).slice(0, 2)).toEqual(reference);
  // Aucun résultat de pari n'y est dévoilé.
  expect(await texteExact(ouverture)).not.toMatch(/OU exclusif|coincé|p − y|3 points/);
  // L'étape 9 : les mêmes prénoms, entre guillemets.
  const etape9 = await texteExact(page.locator('#etape-9 .texte'));
  for (const prenom of reference) expect(etape9).toContain(`«${FINE}${prenom}${FINE}»`);
  // Le nombre de poids du réseau, compté par le Python, aux étapes 3 et 10.
  expect(E.nb_poids).toBe(9);
  expect(await texteExact(page.locator('#etape-3 .texte'))).toContain(`${E.nb_poids} poids`);
  // L'encadré : ton IA, GPT-3 et Llama 3 405B, sourcés.
  const labo = page.locator('#etape-10 .labo');
  const texteLabo = await texteExact(labo);
  expect(texteLabo).toContain(`${E.nb_poids} poids`);
  // « 405 milliards » ne se coupe pas : l'espace avant l'unité est insécable.
  const quantite = (n: number) => formaterQuantite(n).replace(' ', '\u00A0');
  expect(texteLabo).toContain(quantite(PRESETS_FORGE.tres_grand.parametres));
  const liens = await labo.locator('a').evaluateAll((a) => a.map((e) => e.getAttribute('href')));
  for (const id of ['gpt-3-175b', 'llama-3-405b']) {
    const m = modelePublic(id);
    expect(texteLabo, id).toContain(quantite(m.parametres));
    expect(liens, id).toContain(m.source.url);
  }
  // L'« À suivre » nomme le chapitre 1.1, en texte (S3).
  const suite = page.locator('#etape-10 .texte');
  expect(await texteExact(suite)).toContain(typographier(trouverChapitre('1.1').chapitre.titre));
  // Tant que 1.1 n'a pas paru, la phrase le dit, et renvoie par un lien au premier chapitre paru de la Partie 1 ;
  // quand 1.1 aura paru, ni l'un ni l'autre (le pied du chapitre y mène).
  const { partie } = trouverChapitre('1.1');
  const parus = partie.chapitres.filter((c) => existsSync(`src/content/chapitres/${c.numero.replace('.', '-')}.mdx`));
  const aVenir = typographier('n\'a pas encore paru');
  const lienVers = (numero: string) => suite.locator(`a[href="/forge-ia/partie-1/${numero.replace('.', '-')}/"]`);
  if (parus[0]?.numero !== '1.1') {
    expect(await texteExact(suite)).toContain(aVenir);
    if (parus.length > 0) {
      const [premier] = parus;
      await expect(lienVers(premier.numero)).toHaveCount(1);
      expect(await texteExact(lienVers(premier.numero))).toBe(
        typographier(`le chapitre ${premier.numero}, « ${titreCourt(premier.titre)} »`),
      );
    }
  } else {
    expect(await texteExact(suite)).not.toContain(aVenir);
    for (const c of partie.chapitres.filter((c) => c.numero !== '1.1')) await expect(lienVers(c.numero)).toHaveCount(0);
  }
});

test('sans JavaScript, le neurone est sur ET avec 2 points sur 4, et tout se lit', async ({ browser, baseURL }) => {
  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const page = await ctx.newPage();
  await page.goto(PAGE);
  await expect(page.locator('[data-test="ouverture"]')).toBeVisible();
  // L'atelier, net, sur ET, avec le réglage du départ.
  await expect(page.locator('[data-test="neu-porte"][data-porte="et"]')).toHaveAttribute('aria-pressed', 'true');
  expect(await texteExact(page.locator('[data-test="neu-bilan"]'))).toBe('2 points sur 4 bien classés.');
  await expect(page.locator('[data-test="neu-w1"]')).toHaveText('1');
  await expect(page.locator('[data-test="neu-b"]')).toHaveText('0');
  await expect(page.locator('[data-test="neu-dessin"]')).toBeVisible();
  await expect(page.locator('[data-test="neu-droite"]')).toHaveCount(1);
  // Les explications des quatre paris sont données d'emblée ; la courbe, le tableau et l'avant-goût sont là.
  for (const id of PARIS) await expect(page.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  await expect(page.locator('[data-test="courbe-xor"]')).toBeVisible();
  await expect(page.locator('[data-test="predictions"]')).toBeVisible();
  // Les deux sorties, et la phrase des durées.
  await expect(page.locator(`[data-sortie="${FICHIER_PROCESSEUR}"]`)).toBeVisible();
  await expect(page.locator(`[data-sortie="${FICHIER_CARTE}"]`)).toBeVisible();
  await expect(page.locator('[data-test="durees"]')).toBeVisible();
  const tableau = page.locator('[data-test="mini-avant-apres"]');
  await verifierStructureAvantApres(tableau, AVANT_GOUT.nbEchantillons);
  await verifierDroiteEnTirets(tableau, AVANT_GOUT.nbEchantillons);
  await expect(page.locator('#etape-10 .labo')).toBeVisible();
  await verifierSansDebordement(page);
  await ctx.close();
});
