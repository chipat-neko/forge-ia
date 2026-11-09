// Parcours du chapitre 1.4, « Le transformer, pièce par pièce » : un brouillon
// (src/brouillons/chapitres/1-4.mdx) tant qu'il n'a pas paru, construit à son
// adresse définitive avec FORGE_ESSAIS=1.
//
// Les attendus viennent des jumeaux (rope.ts, parametres.ts), des paris
// (paris-1-4.ts), de la section residus des attendus du projet 1.4 et des
// attendus de l'attention du mini-modèle, lus sur le disque : un parcours, chargé
// par Node sans Vite, n'importe ni ?raw, ni .json, ni astro:* (P8). Il ne passe
// donc pas par paris-attention.ts, qui lit l'exemple de l'attention en .json :
// les paris « regard » et « masque » se vérifient sur les poids du Python, comme
// dans e2e/attention.spec.ts. Le code montré est relu dans les fichiers du
// projet et de forge, tels qu'ils sont aujourd'hui.
import { readFileSync } from 'node:fs';
import { test, expect, type Page } from '@playwright/test';
import type { Choix } from '../src/lib/choix';
import { largeurCachee, nombreParametres, PRESETS_FORGE } from '../src/lib/calculateur/ton-ia';
import { depuisHex } from '../src/lib/mini-modele/calcul';
import { nombre } from '../src/lib/nombres';
import { trouverChapitre } from '../src/lib/parcours';
import { MESURES_PARTIE_1 } from '../src/lib/partie-1/mesures';
import { nombresDeTetes } from '../src/lib/partie-1/parametres';
import {
  BASE_ROPE,
  choixOuSontLesParametres,
  choixResidus,
  choixRopeRapide,
  etatDeLAtelier,
  etatDuDefi,
  FIGURE_ROPE,
  phraseDeLAtelier,
  placeParmiLesTailles,
  POSITION_INITIALE,
  texteDegres,
  type ResidusDuPari,
} from '../src/lib/partie-1/paris-1-4';
import { anglesRope } from '../src/lib/partie-1/rope';
import { extraireRegion } from '../src/lib/regions';
import { lireSortie } from '../src/lib/sorties';
import { extraireSymbole } from '../src/lib/symboles';
import { typographier } from '../src/lib/typo';
import {
  attendreHydratation as attendreLesIlots,
  plusLongueLigne,
  texteHorsCode,
  verifierAxe,
  verifierLiensVersParus,
  verifierSansDebordement,
  verifierTypographieHorsCode,
  verifierVoisin,
} from './outils';

const PAGE = '/forge-ia/partie-1/1-4/';
const FINE = '\u202F';

// Playwright tourne dans site/ : le dépôt est un dossier plus haut.
const ATTENDUS = JSON.parse(readFileSync('../projets/1.4-transformer/tests/attendus.json', 'utf8')) as { residus: ResidusDuPari };
const RESIDUS = ATTENDUS.residus;
const TON_IA = PRESETS_FORGE.tres_grand;
// Les poids de l'exemple de l'attention, écrits par le Python (chaque flottant en 16 chiffres hexadécimaux).
const ATTENTION = JSON.parse(readFileSync('../projets/mini-modele/tests/attendus-attention.json', 'utf8')) as {
  jetons: string[];
  tetes: { nom: string; poids: string[][] }[];
};
const POIDS = ATTENTION.tetes.map((t) => t.poids.map((ligne) => ligne.map(depuisHex)));
const JETONS = ATTENTION.jetons;
/** « il » (le mot 6) dans la tête « de qui on parle » (la tête 1), comme paris-attention.ts. */
const IL = 6;
const DE_QUI_ON_PARLE = 1;
const FORGERON = 1;

// Ce qui n'est pas du texte du chapitre mais des données brutes : les mots de la phrase de
// l'animation de l'attention (le moteur du plan 3, inchangé), et le texte du schéma (SVG).
const BRUT = '[data-attention], [data-test="schema"] svg';

/**
 * Attend que les trois îlots de la page (l'animation de l'attention, la figure de RoPE et
 * l'atelier) soient hydratés, avec l'aide commune, mais jusqu'à 20 s au lieu de 5. Juste après
 * la construction, la première visite lit des fichiers neufs, et leur premier chargement a pris
 * jusqu'à 5,4 s sur ce PC, pour toutes les pages (1.1 et 1.2 comprises) ; ensuite, la page se
 * charge en 0,3 s et ses îlots s'hydratent en moins de 0,1 s (mesuré le 9 novembre 2026, quatre
 * pages à la fois). Trois îlots à charger, au lieu d'un, dépassaient parfois les 5 s.
 */
async function attendreHydratation(page: Page): Promise<void> {
  await attendreLesIlots(page, 20_000);
}

/** Le texte exact d'un élément (textContent : toHaveText ramènerait U+202F à une espace ordinaire). */
async function texteExact(page: Page, selecteur: string): Promise<string> {
  return (await page.locator(selecteur).textContent()) ?? '';
}

/** Attend la fin des animations en cours (fondu des verrous, verdict des paris) : axe mesure alors les vraies couleurs. */
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

/** Règle un nombre jaune au clavier : Début, puis `crans` fois la flèche droite. */
async function regler(page: Page, testId: string, crans: number): Promise<void> {
  const nombreJaune = page.locator(`[data-test="${testId}"]`);
  await nombreJaune.focus();
  await page.keyboard.press('Home');
  for (let i = 0; i < crans; i++) await page.keyboard.press('ArrowRight');
}

/** Ouvre la page et fait le pari de l'étape 8, qui ouvre l'atelier. */
async function ouvrirAtelier(page: Page): Promise<void> {
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="parametres"] [data-juste]').click();
  await expect(page.locator('[data-verrou="atelier"]')).toHaveCSS('opacity', '1');
}

/** Ce que l'atelier affiche de son réglage : la largeur, les blocs et les têtes, lus dans les nombres jaunes. */
async function reglage(page: Page): Promise<{ dim: number; couches: number; tetes: number }> {
  const lire = async (id: string) => Number(((await page.locator(`[data-test="${id}"]`).textContent()) ?? '').replace(/\D/g, ''));
  return { dim: await lire('par-dim'), couches: await lire('par-couches'), tetes: await lire('par-tetes') };
}

/** Vérifie tout ce que l'atelier dit d'un réglage, face à etatDeLAtelier. */
async function verifierAtelier(page: Page, dim: number, couches: number, tetes: number): Promise<void> {
  const nom = `${dim}, ${couches} blocs, ${tetes} têtes`;
  expect(await reglage(page), nom).toStrictEqual({ dim, couches, tetes });
  const e = etatDeLAtelier(dim, couches, tetes);
  expect(await texteExact(page, '[data-test="par-phrase"]'), nom).toBe(phraseDeLAtelier(e));
  expect(await texteExact(page, '[data-test="par-total"]'), nom).toBe(nombre(e.total));
  expect(await texteExact(page, '[data-test="par-place"]'), nom).toBe(placeParmiLesTailles(e));
  expect(await texteExact(page, '[data-test="par-defi"]'), nom).toBe(etatDuDefi(e).texte);
  const lignes = page.locator('[data-test="par-repartition"] tbody tr[data-famille]');
  expect(await lignes.evaluateAll((l) => l.map((x) => [x.getAttribute('data-famille'), Number(x.getAttribute('data-parametres'))])), nom).toStrictEqual(
    Object.entries(e.repartition),
  );
}

/** Le transform calculé d'une aiguille : [cos, sin] de son angle, lus dans sa matrice. */
async function rotation(page: Page, paire: number): Promise<[number, number]> {
  return page.locator(`[data-aiguille="${paire}"]`).evaluate((g) => {
    const m = /matrix\(([^)]+)\)/.exec(getComputedStyle(g).transform);
    if (!m) return [Number.NaN, Number.NaN];
    const [a, b] = m[1].split(',').map(Number);
    return [a, b];
  });
}

/** Les aiguilles qui glissent : les animations en cours sur une aiguille de la figure. */
async function aiguillesQuiGlissent(page: Page): Promise<number> {
  return page.evaluate(
    () => document.getAnimations().filter((a) => (a.effect as KeyframeEffect | null)?.target?.closest?.('[data-aiguille]')).length,
  );
}

test('chapitre 1.4 complet', async ({ page }, info) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  const { total } = trouverChapitre('1.4');
  expect(total).toBe(21);
  await expect(page.locator('header')).toContainText(`Partie 1, chapitre 1.4 sur ${total}`);
  if (info.project.name === 'mobile') expect(page.viewportSize()?.width).toBe(390);
  await expect(page.locator('.pari[data-pari]')).toHaveCount(5);
  await page.locator('[data-pari="regard"] [data-juste]').click();
  await page.locator('[data-pari="masque"] [data-juste]').click();
  await page.locator('[data-pari="rope"] [data-juste]').click();
  await expect(page.locator('[data-verrou="rope"]')).not.toHaveAttribute('inert', '');
  await page.locator('[data-pari="residus"] [data-juste]').click();
  await page.locator('[data-pari="parametres"] [data-juste]').click();
  await expect(page.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  // Changer un réglage de l'atelier fait gagner son acquis.
  await expect(page.locator('#recap [data-acquis="atelier"]')).not.toHaveAttribute('data-gagne', 'oui');
  await page.locator('[data-test="par-couches"]').focus();
  await page.keyboard.press('ArrowLeft');
  await expect(page.locator('#recap [data-acquis="atelier"]')).toHaveAttribute('data-gagne', 'oui');
  await expect(page.locator('#recap [data-total]')).toContainText('6 sur 6');
  // Le pied suit les fichiers : 1.3 a paru, 1.5 est « à venir » tant qu'il n'a pas paru.
  await verifierVoisin(page, 'precedent', '1-3.mdx', '/forge-ia/partie-1/1-3/');
  await verifierVoisin(page, 'suivant', '1-5.mdx', '/forge-ia/partie-1/1-5/');
  await verifierLiensVersParus(page.locator('main'), PAGE);
  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
  await verifierTypographieHorsCode(page.locator('main'), BRUT);
  // Aucune expression du MDX restée en texte (une accolade tombée dans un passage de code, par exemple).
  expect(await texteHorsCode(page.locator('main'))).not.toMatch(/[{}]/);
  expect(await page.locator('main code').allTextContents()).not.toContainEqual(expect.stringMatching(/[{}]/));
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);
});

test('les choix des paris viennent des jumeaux et des attendus', async ({ page }) => {
  await page.goto(PAGE);
  // Le pari « regard » : la bonne réponse est le mot que « il » regarde le plus dans la tête « de qui on
  // parle » ; les deux autres sont des mots de la phrase, dont « puis », dans l'ordre de la phrase.
  const poidsDeIl = POIDS[DE_QUI_ON_PARLE][IL].slice(0, IL + 1);
  const plusRegarde = JETONS[poidsDeIl.indexOf(Math.max(...poidsDeIl))];
  expect(plusRegarde).toBe('forgeron');
  await expect(page.locator('[data-pari="regard"] [data-juste]')).toHaveText(plusRegarde);
  const regard = await page.locator('[data-pari="regard"] button[data-choix]').allTextContents();
  expect(regard).toHaveLength(3);
  expect(regard).toContain('puis');
  const rangs = regard.map((mot) => JETONS.slice(0, IL + 1).indexOf(mot));
  expect(rangs.every((r) => r >= 0)).toBe(true);
  expect([...rangs].sort((a, b) => a - b)).toStrictEqual(rangs);
  // Le pari « masque » : « forgeron » ne voit pas « il », dans aucune tête.
  for (const poids of POIDS) expect(poids[FORGERON][IL]).toBe(0);
  expect(await page.locator('[data-pari="masque"] button[data-choix]').allTextContents()).toStrictEqual(['0', 'environ la moitié', 'presque tout']);
  await expect(page.locator('[data-pari="masque"] [data-juste]')).toHaveText('0');

  const paris: [string, Choix[]][] = [
    ['rope', choixRopeRapide()],
    ['residus', choixResidus(RESIDUS)],
    ['parametres', choixOuSontLesParametres()],
  ];
  for (const [id, choix] of paris) {
    const boutons = page.locator(`[data-pari="${id}"] button[data-choix]`);
    expect(await boutons.allTextContents(), id).toEqual(choix.map(affiche));
    expect(await page.locator(`[data-pari="${id}"] [data-juste]`).textContent(), id).toBe(affiche(choix.find((c) => c.juste)!));
  }
  // Le pari residus : sans le x +, les deux textes sortent pareils.
  await expect(page.locator('[data-pari="residus"] [data-juste]')).toContainText('les deux suites sortent pareilles');
  // L'acquis du x + : le récapitulatif n'écrit pas de code, l'espace y est insécable.
  expect(await page.locator('#recap [data-acquis="residus"]').textContent()).toContain('x\u00A0+');
  await expect(page.locator('[data-pari="parametres"] [data-juste]')).toHaveText('Les MLP');
});

test('le code affiché est celui des régions du projet et des symboles de forge, tels qu’ils sont aujourd’hui', async ({ page }) => {
  await page.goto(PAGE);
  const pieces = 'projets/1.4-transformer/transformer_pas_a_pas/pieces.py';
  const forge = 'projets/forge/forge/modele/transformer.py';
  const blocs: [string, 'symbole' | 'region', string][] = [
    [pieces, 'region', 'plongement'],
    [pieces, 'region', 'modele'],
    [pieces, 'region', 'attention'],
    [forge, 'symbole', 'MLP.forward'],
    [forge, 'symbole', 'Bloc.forward'],
    ['projets/1.4-transformer/tests/test_pieces.py', 'region', 'test-egalite'],
  ];
  const codes = page.locator('.code-explique');
  await expect(codes).toHaveCount(blocs.length);
  for (const [i, [fichier, sorte, nom]] of blocs.entries()) {
    const source = readFileSync(`../${fichier}`, 'utf8');
    const attendu = sorte === 'region' ? extraireRegion(source, nom, fichier) : extraireSymbole(source, nom, fichier, { docstring: false });
    expect(await codes.nth(i).locator('pre').evaluate((pre) => pre.textContent), nom).toBe(attendu);
    await expect(codes.nth(i).locator('figcaption a')).toHaveAttribute('href', `https://github.com/chipat-neko/forge-ia/blob/main/${fichier}`);
  }
  // Le code de forge montré est bien du code de forge : le x + du bloc, la porte du MLP.
  expect(await codes.nth(4).locator('pre').textContent()).toContain('x = x + self.attention(');
  expect(await codes.nth(3).locator('pre').textContent()).toContain('F.silu(self.proj_porte(x))');
  // La sortie de la comparaison est celle du fichier enregistré par le projet.
  const sortie = lireSortie(readFileSync(`../${MESURES_PARTIE_1.sortieComparaison}`, 'utf8'), MESURES_PARTIE_1.sortieComparaison);
  expect(sortie).not.toBeNull();
  expect(await page.locator(`[data-sortie="${MESURES_PARTIE_1.sortieComparaison}"] [data-contenu]`).textContent()).toBe(sortie!.contenu);
  await expect(page.getByRole('link', { name: 'Le projet complet' })).toHaveAttribute(
    'href',
    'https://github.com/chipat-neko/forge-ia/tree/main/projets/1.4-transformer',
  );
});

test('le schéma : les nombres de très grand, un titre, une description et une liste en texte', async ({ page }) => {
  await page.goto(PAGE);
  const schema = page.locator('[data-test="schema"]');
  const svg = schema.locator('svg');
  await expect(svg).toHaveAttribute('role', 'img');
  const titre = (await svg.locator('title').textContent()) ?? '';
  const desc = (await svg.locator('desc').textContent()) ?? '';
  expect(titre.length).toBeGreaterThan(10);
  expect(desc.length).toBeGreaterThan(20);
  await expect(svg).toHaveAccessibleName(titre);
  // Ce que le dessin montre, en nombres de très grand.
  const dessin = (await svg.textContent()) ?? '';
  for (const n of [`× ${TON_IA.couches}`, nombre(TON_IA.dim), nombre(TON_IA.vocabulaire), nombre(largeurCachee(TON_IA.dim))]) {
    expect(dessin, n).toContain(n);
  }
  for (const mot of ['plongement', 'attention', 'MLP', 'RMSNorm', 'logits']) expect(dessin, mot).toContain(mot);
  // La liste équivalente : une entrée par étage du dessin, avec les mêmes nombres.
  const liste = schema.locator('[data-test="schema-liste"] li');
  await expect(liste).toHaveCount(5);
  const texte = (await schema.locator('[data-test="schema-liste"]').textContent()) ?? '';
  for (const n of [nombre(TON_IA.couches), nombre(TON_IA.dim), nombre(TON_IA.tetes), nombre(TON_IA.dim / TON_IA.tetes), nombre(TON_IA.vocabulaire), nombre(TON_IA.contexte)]) {
    expect(texte, n).toContain(n);
  }
});

test('la figure de RoPE : les angles de anglesRope, et l’aiguille glisse seulement si le lecteur l’accepte', async ({ page }) => {
  // Le lecteur accepte le mouvement (le réglage du système de la machine de test ne compte pas).
  await page.emulateMedia({ reducedMotion: 'no-preference' });
  await page.goto(PAGE);
  await attendreHydratation(page);
  // Avant le pari, la position est désactivée.
  await expect(page.locator('[data-test="rope-position"]')).toHaveAttribute('aria-disabled', 'true');
  await page.locator('[data-pari="rope"] [data-juste]').click();
  await expect(page.locator('[data-verrou="rope"]')).toHaveCSS('opacity', '1');
  const position = page.locator('[data-test="rope-position"]');
  await expect(position).toHaveAttribute('aria-valuenow', String(POSITION_INITIALE));
  await expect(position).toHaveAttribute('aria-valuemax', String(FIGURE_ROPE.positionMax));
  const verifierAngles = async (p: number) => {
    const angles = anglesRope(p, FIGURE_ROPE.dimTete, BASE_ROPE);
    for (const [i, a] of angles.entries()) {
      await expect(page.locator(`[data-aiguille="${i}"]`)).toHaveAttribute('data-angle', String(a));
      expect(await texteExact(page, `[data-test="rope-angle-${i}"]`), `position ${p}, paire ${i + 1}`).toBe(texteDegres(a));
    }
  };
  await verifierAngles(POSITION_INITIALE);
  // Avec le mouvement permis, les aiguilles glissent vers leur nouvel angle.
  await position.focus();
  await page.keyboard.press('ArrowRight');
  await expect(position).toHaveAttribute('aria-valuenow', String(POSITION_INITIALE + 1));
  expect(await aiguillesQuiGlissent(page)).toBeGreaterThan(0);
  await verifierAngles(POSITION_INITIALE + 1);
  await page.keyboard.press('End');
  await verifierAngles(FIGURE_ROPE.positionMax);
  await attendreAnimations(page);
  await verifierAxe(page);
  await verifierSansDebordement(page);
});

test('sous prefers-reduced-motion, l’aiguille se pose sans glisser', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto(PAGE);
  await attendreHydratation(page);
  await page.locator('[data-pari="rope"] [data-juste]').click();
  const position = page.locator('[data-test="rope-position"]');
  await expect(position).not.toHaveAttribute('aria-disabled', 'true');
  await position.focus();
  for (const touche of ['ArrowRight', 'ArrowRight', 'End', 'Home', 'ArrowRight']) {
    await page.keyboard.press(touche);
    const p = Number(await position.getAttribute('aria-valuenow'));
    // Aucune animation, et l'aiguille est déjà à son angle.
    expect(await aiguillesQuiGlissent(page), touche).toBe(0);
    const angles = anglesRope(p, FIGURE_ROPE.dimTete, BASE_ROPE);
    for (const [i, a] of angles.entries()) {
      const [c, s] = await rotation(page, i);
      expect(Math.abs(c - Math.cos(a)), `position ${p}, paire ${i + 1}`).toBeLessThan(1e-4);
      expect(Math.abs(s - Math.sin(a)), `position ${p}, paire ${i + 1}`).toBeLessThan(1e-4);
    }
  }
});

test('atelier : seulement des têtes possibles, et le nombre de ton IA lu dans nombreParametres', async ({ page }) => {
  await ouvrirAtelier(page);
  // À l'arrivée : ton IA, son nombre de paramètres, celui de nombreParametres (jamais tapé).
  const n = nombreParametres({
    tailleVocabulaire: TON_IA.vocabulaire,
    dim: TON_IA.dim,
    couches: TON_IA.couches,
    tetes: TON_IA.tetes,
    longueurContexte: TON_IA.contexte,
  });
  expect(n).toBe(TON_IA.parametres);
  expect(await texteExact(page, '[data-test="par-total"]')).toBe(nombre(n));
  await verifierAtelier(page, TON_IA.dim, TON_IA.couches, TON_IA.tetes);
  await expect(page.locator('[data-test="par-tailles"] button[aria-pressed="true"]')).toHaveAttribute('data-preset', 'tres_grand');

  // Les têtes, d'un bout à l'autre : exactement les nombres qui partagent dim en parts paires.
  const parcourirLesTetes = async (dim: number): Promise<number[]> => {
    const tetes = page.locator('[data-test="par-tetes"]');
    await tetes.focus();
    await page.keyboard.press('Home');
    const vues: number[] = [];
    for (;;) {
      vues.push((await reglage(page)).tetes);
      const avant = await tetes.getAttribute('aria-valuenow');
      await page.keyboard.press('ArrowRight');
      if ((await tetes.getAttribute('aria-valuenow')) === avant) break;
    }
    for (const t of vues) {
      expect(dim % t, `${dim} / ${t}`).toBe(0);
      expect((dim / t) % 2, `${dim} / ${t}`).toBe(0);
    }
    return vues;
  };
  expect(await parcourirLesTetes(TON_IA.dim)).toStrictEqual(nombresDeTetes(TON_IA.dim));
  // Une largeur de 64 × 19 = 1 216 : d'autres têtes possibles, dont aucune ne laisse une part impaire.
  await regler(page, 'par-dim', 18);
  expect((await reglage(page)).dim).toBe(1216);
  expect(await parcourirLesTetes(1216)).toStrictEqual(nombresDeTetes(1216));

  // Chaque taille de forge, d'un clic : son nombre exact.
  for (const cle of ['mini', 'petit', 'moyen', 'grand', 'tres_grand'] as const) {
    await page.locator(`[data-test="par-tailles"] button[data-preset="${cle}"]`).click();
    const f = PRESETS_FORGE[cle];
    await verifierAtelier(page, f.dim, f.couches, f.tetes);
    await expect(page.locator(`[data-test="par-tailles"] button[data-preset="${cle}"]`)).toHaveAttribute('aria-pressed', 'true');
  }

  // Le défi : petit, plus un bloc.
  const defi = page.locator('[data-defi]');
  await page.locator('[data-test="par-tailles"] button[data-preset="petit"]').click();
  await expect(defi).not.toHaveClass(/\breussi\b/);
  await page.locator('[data-test="par-couches"]').focus();
  await page.keyboard.press('ArrowRight');
  await verifierAtelier(page, PRESETS_FORGE.petit.dim, PRESETS_FORGE.petit.couches + 1, PRESETS_FORGE.petit.tetes);
  await expect(defi).toHaveClass(/\breussi\b/);
  await expect(defi.locator('[role="status"]')).toContainText(`Défi réussi${FINE}:`);
  // Jamais de valeur absurde, et rien ne déborde, même au plus grand réglage.
  await regler(page, 'par-dim', 100);
  await regler(page, 'par-couches', 100);
  expect(await page.locator('[data-atelier-parametres]').innerText()).not.toMatch(/NaN|Infinity|undefined|\de\+/);
  await verifierSansDebordement(page);
  await verifierAxe(page);
});

test('avant les paris, la figure et l’atelier sont verrouillés ; sans JavaScript, tout se lit', async ({ page, browser, baseURL }) => {
  await page.goto(PAGE);
  await attendreHydratation(page);
  for (const nom of ['attention', 'rope', 'atelier']) {
    await expect(page.locator(`[data-verrou="${nom}"]`)).toHaveAttribute('inert', '');
  }
  await expect(page.locator('[data-test="par-dim"]')).toHaveAttribute('aria-disabled', 'true');
  await verifierAxe(page);
  await verifierSansDebordement(page);
  const { longueur, ligne } = await plusLongueLigne(page);
  expect(longueur, `ligne la plus longue : « ${ligne} »`).toBeLessThanOrEqual(80);

  const ctx = await browser.newContext({ javaScriptEnabled: false, baseURL });
  const sansJs = await ctx.newPage();
  await sansJs.goto(PAGE);
  // Pas de verrou : la figure et l'atelier sont là, avec leurs valeurs de départ.
  await expect(sansJs.locator('[data-verrou="atelier"]')).not.toHaveAttribute('inert', '');
  await expect(sansJs.locator('[data-test="par-total"]')).toHaveText(nombre(TON_IA.parametres));
  await expect(sansJs.locator('[data-aiguille="0"]')).toHaveAttribute('data-angle', String(anglesRope(POSITION_INITIALE, FIGURE_ROPE.dimTete, BASE_ROPE)[0]));
  // Les explications des paris sont données d'emblée.
  for (const id of ['regard', 'masque', 'rope', 'residus', 'parametres']) {
    await expect(sansJs.locator(`[data-pari="${id}"] .verdict`)).toBeVisible();
  }
  await expect(sansJs.locator('[data-test="schema"]')).toBeVisible();
  await ctx.close();
});
