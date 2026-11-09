// Le modèle de langage à n-grammes du chapitre 1.1, en TypeScript.
//
// C'est le jumeau exact de projets/1.1-modele-de-langage/modele_de_langage/
// ngrammes.py : mêmes fonctions, mêmes opérations, dans le même ordre. Le
// fichier projets/1.1-modele-de-langage/tests/attendus.json, calculé par le
// Python, le prouve dans ngrammes.test.ts, et la page d'essai de parité le
// vérifie dans Chrome, Firefox et WebKit. Si l'un des deux change, l'autre
// doit suivre.
//
// Pourquoi le résultat est le même au bit près : les comptes sont des entiers,
// les probabilités une seule division, et les poids des comptes, leurs carrés ou
// une racine carrée, que la norme IEEE 754 arrondit au plus juste dans les deux langages.
// Les sommes se font dans une boucle, de gauche à droite, comme en Python. La
// perplexité (exp et log) reste en Python : le site lit ses valeurs dans les
// attendus (perplexites-1-1.ts).
//
// Les caractères sont des points de code Unicode, comme les `str` de Python :
// Array.from les sépare (« 😀 » compte pour un, et non deux), et les tris
// passent par comparerPointsDeCode (le « < » de JavaScript compare des unités
// UTF-16, et rangerait « 😀 » avant « U+FF5E »).
//
// Ce module n'importe que calcul.ts et points-de-code.ts, qui n'importent
// rien, et il prend le texte en argument : un parcours de test peut l'importer
// (aucun ?raw, aucun .json). Le texte du site est dans texte-1-1.ts.

import { Hasard } from '../mini-modele/calcul';
import { comparerPointsDeCode } from '../points-de-code';

export const ORDRE_MAX = 6;

/** Les températures du site : 0 choisit le plus probable, 1 suit les probabilités, 0,5 les durcit, 2 les adoucit. */
export const TEMPERATURES: readonly number[] = Object.freeze([0, 0.5, 1, 2]);

// Les messages sont ceux du Python, mot pour mot.
export const MESSAGE_TEXTE_VIDE = 'Le texte est vide : il faut au moins un caractère.';
export const MESSAGE_CONTEXTE_COURT = 'Il faut au moins n caractères de contexte.';
export const MESSAGE_AUCUN_POIDS = 'Aucun poids positif : il faut au moins un poids plus grand que 0 pour tirer.';
export const MESSAGE_TEMPERATURE = "La température doit valoir 0, 0.5, 1 ou 2 : choisis l'une de ces quatre valeurs.";

/** Pour chaque contexte, combien de fois chaque caractère le suit (dans l'ordre de première apparition). */
export type Comptes = Map<string, Map<string, number>>;

const AUCUN_COMPTE: ReadonlyMap<string, number> = new Map();

/** Sépare le texte : les 90 premiers % pour apprendre, le reste pour vérifier (en points de code). */
export function couper(texte: string): [string, string] {
  const points = Array.from(texte);
  const limite = Math.floor((points.length * 9) / 10);
  return [points.slice(0, limite).join(''), points.slice(limite).join('')];
}

/** Les caractères distincts du texte, triés par point de code. */
export function alphabet(texte: string): string[] {
  return [...new Set(Array.from(texte))].sort(comparerPointsDeCode);
}

/**
 * Pour chaque contexte de n caractères, combien de fois chaque caractère le suit.
 * Pour n = 0, le contexte est le texte vide : on compte les caractères tout court.
 */
export function compter(texte: string, n: number): Comptes {
  const points = Array.from(texte);
  // Sans caractère hors du premier plan, une unité UTF-16 est un point de code : slice suffit.
  const simple = points.length === texte.length;
  const comptes: Comptes = new Map();
  for (let i = n; i < points.length; i++) {
    const contexte = simple ? texte.slice(i - n, i) : points.slice(i - n, i).join('');
    let suivants = comptes.get(contexte);
    if (suivants === undefined) {
      suivants = new Map();
      comptes.set(contexte, suivants);
    }
    const c = points[i];
    suivants.set(c, (suivants.get(c) ?? 0) + 1);
  }
  return comptes;
}

/** Les comptes de tous les ordres de 0 à n : [compter(texte, 0), …, compter(texte, n)]. generer s'en sert pour reculer d'un ordre. */
export function compterParOrdre(texte: string, n: number): Comptes[] {
  const comptes: Comptes[] = [];
  for (let k = 0; k <= n; k++) comptes.push(compter(texte, k));
  return comptes;
}

/** Les n derniers caractères du contexte (le texte vide pour n = 0). */
export function finDuContexte(contexte: string, n: number): string {
  const points = Array.from(contexte);
  if (points.length < n) throw new RangeError(MESSAGE_CONTEXTE_COURT);
  return points.slice(points.length - n).join('');
}

/**
 * La probabilité de chaque caractère après ce contexte, du plus probable au
 * moins probable (à égalité, le plus petit point de code d'abord).
 *
 * Lissage de Laplace : on ajoute 1 au compte de chaque caractère de
 * l'alphabet ; un contexte jamais vu donne la même probabilité à tous.
 */
export function distribution(
  comptes: ReadonlyMap<string, ReadonlyMap<string, number>>,
  lettres: readonly string[],
  contexte: string,
  n: number,
): [string, number][] {
  if (lettres.length === 0) throw new RangeError(MESSAGE_TEXTE_VIDE);
  const suivants = comptes.get(finDuContexte(contexte, n)) ?? AUCUN_COMPTE;
  let total = 0;
  for (const k of suivants.values()) total += k;
  const v = lettres.length;
  const probabilites: [string, number][] = lettres.map((c) => [c, ((suivants.get(c) ?? 0) + 1) / (total + v)]);
  return probabilites.sort((a, b) => (a[1] > b[1] ? -1 : a[1] < b[1] ? 1 : comparerPointsDeCode(a[0], b[0])));
}

/**
 * Le poids de chaque caractère de l'alphabet, dans l'ordre de l'alphabet, pour
 * tirer au sort. On part des comptes bruts : un caractère jamais vu après ce
 * contexte a un poids nul. 1 suit les probabilités (le compte), 0,5 les durcit
 * (le carré), 2 les adoucit (la racine carrée), et 0 ne garde que le plus compté.
 */
export function poids(
  suivants: ReadonlyMap<string, number>,
  lettres: readonly string[],
  temperature: number,
): number[] {
  const comptes = lettres.map((c) => suivants.get(c) ?? 0);
  if (temperature === 1) return comptes;
  if (temperature === 0.5) return comptes.map((k) => k * k);
  if (temperature === 2) return comptes.map((k) => Math.sqrt(k));
  if (temperature === 0) {
    // Le premier des plus comptés : l'alphabet est trié, donc le plus petit point de code.
    let meilleur = -1;
    let record = 0;
    comptes.forEach((k, i) => {
      if (k > record) {
        meilleur = i;
        record = k;
      }
    });
    const gagnant = comptes.map(() => 0);
    if (meilleur >= 0) gagnant[meilleur] = 1;
    return gagnant;
  }
  throw new RangeError(MESSAGE_TEMPERATURE);
}

/** L'indice tiré par u, un nombre de [0, 1[ : on pose les poids bout à bout, et u en choisit un. */
export function tirer(lesPoids: readonly number[], u: number): number {
  let total = 0.0;
  for (const p of lesPoids) total += p;
  const cible = u * total;
  let cumul = 0.0;
  for (let i = 0; i < lesPoids.length; i++) {
    cumul += lesPoids[i];
    if (cumul > cible) return i;
  }
  // Seul un arrondi peut venir ici : le dernier poids non nul est tiré.
  for (let i = lesPoids.length - 1; i >= 0; i--) {
    if (lesPoids[i] > 0) return i;
  }
  throw new RangeError(MESSAGE_AUCUN_POIDS);
}

/**
 * Le départ, suivi de `longueur` caractères tirés un à un d'après les n derniers.
 * comptesParOrdre[k] contient les comptes de l'ordre k, de 0 à n (compterParOrdre).
 * Quand les n derniers caractères n'ont jamais été vus, le modèle recule : les
 * n − 1 derniers, puis n − 2, jusqu'à 0, toujours connu. On ne tire que parmi les
 * caractères déjà vus. Un tirage par caractère, avec le Hasard du mini-modèle :
 * la même graine donne le même texte que le Python.
 */
export function generer(
  comptesParOrdre: readonly ReadonlyMap<string, ReadonlyMap<string, number>>[],
  lettres: readonly string[],
  n: number,
  depart: string,
  longueur: number,
  temperature: number,
  graine: number,
): string {
  if (lettres.length === 0) throw new RangeError(MESSAGE_TEXTE_VIDE);
  finDuContexte(depart, n); // lève l'erreur si le départ est trop court
  const hasard = new Hasard(graine);
  const texte = Array.from(depart);
  for (let i = 0; i < longueur; i++) {
    let suivants: ReadonlyMap<string, number> | undefined;
    for (let k = n; k >= 0; k--) {
      suivants = comptesParOrdre[k].get(texte.slice(texte.length - k).join(''));
      if (suivants !== undefined) break;
    }
    if (suivants === undefined) throw new RangeError(MESSAGE_TEXTE_VIDE);
    const p = poids(suivants, lettres, temperature);
    texte.push(lettres[tirer(p, hasard.uniforme())]);
  }
  return texte.join('');
}

/**
 * Ce que generer tirerait après ce contexte : l'ordre utilisé, puis la chance
 * de chaque caractère. Comme generer, on recule tant que les k derniers
 * caractères n'ont jamais été vus (k = n, puis n − 1, … jusqu'à 0). La chance
 * d'un caractère est son poids, à cette température, divisé par le total des
 * poids. Seuls les caractères de poids non nul sont rendus, du plus probable au
 * moins probable (à égalité, le plus petit point de code d'abord).
 */
export function tirage(
  comptesParOrdre: readonly ReadonlyMap<string, ReadonlyMap<string, number>>[],
  lettres: readonly string[],
  contexte: string,
  n: number,
  temperature: number,
): [number, [string, number][]] {
  if (lettres.length === 0) throw new RangeError(MESSAGE_TEXTE_VIDE);
  finDuContexte(contexte, n); // lève l'erreur si le contexte est trop court
  const points = Array.from(contexte);
  let suivants: ReadonlyMap<string, number> | undefined;
  let ordre = n;
  for (let k = n; k >= 0; k--) {
    suivants = comptesParOrdre[k].get(points.slice(points.length - k).join(''));
    if (suivants !== undefined) {
      ordre = k;
      break;
    }
  }
  if (suivants === undefined) throw new RangeError(MESSAGE_TEXTE_VIDE);
  const lesPoids = poids(suivants, lettres, temperature);
  let total = 0.0;
  for (const p of lesPoids) total += p;
  const chances: [string, number][] = [];
  lettres.forEach((c, i) => {
    if (lesPoids[i] > 0) chances.push([c, lesPoids[i] / total]);
  });
  return [ordre, chances.sort((a, b) => (a[1] > b[1] ? -1 : a[1] < b[1] ? 1 : comparerPointsDeCode(a[0], b[0])))];
}

/** Combien de contextes du texte de validation le modèle n'a jamais vus, et combien il y en a. */
export function partJamaisVue(
  comptes: ReadonlyMap<string, ReadonlyMap<string, number>>,
  validation: string,
  n: number,
): [number, number] {
  const points = Array.from(validation);
  let absents = 0;
  let total = 0;
  for (let i = n; i < points.length; i++) {
    total += 1;
    if (!comptes.has(points.slice(i - n, i).join(''))) absents += 1;
  }
  return [absents, total];
}

/** Vrai si les `longueur` derniers caractères du texte sont déjà apparus plus tôt. */
export function tourneEnRond(texte: string, longueur = 20): boolean {
  const points = Array.from(texte);
  if (points.length <= longueur) return false;
  const fin = points.slice(points.length - longueur).join('');
  // Les positions sont en unités UTF-16 des deux côtés : la comparaison reste juste.
  return texte.indexOf(fin) < texte.length - fin.length;
}
