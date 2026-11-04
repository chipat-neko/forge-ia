// Le mot suivant du chapitre 0.1, en TypeScript, pour l'atelier du navigateur.
//
// C'est le jumeau exact de projets/0.1-python/mot_suivant/mots.py : mêmes
// mots, mêmes comptes, mêmes prédictions, mêmes suites. Le fichier
// projets/0.1-python/tests/attendus.json, calculé par le Python, le prouve
// dans mot-suivant.test.ts, et la page d'essai de parité le vérifie dans
// Chrome, Firefox et WebKit. Si l'un des deux change, l'autre doit suivre.
//
// Deux précautions rendent le résultat identique d'un langage à l'autre :
//  - les minuscules : toLowerCase() et str.lower() suivent tous deux les
//    correspondances complètes d'Unicode (« İ » donne « i » et un point
//    suscrivant, que LETTRES ne contient pas) ;
//  - les égalités se départagent par point de code (comme Python), et non par
//    unité UTF-16 (comme le « < » de JavaScript sur les chaînes).
//
// Ce module n'importe que le comparateur : un parcours de test peut l'importer
// (aucun ?raw, aucun .json). Le texte du projet est dans texte-0-1.ts.

import { comparerPointsDeCode } from '../points-de-code';

/** Les lettres d'un mot, en minuscules : l'alphabet, puis les lettres accentuées du français. */
export const LETTRES = 'abcdefghijklmnopqrstuvwxyzàâäçéèêëîïôöùûüÿœæ';

// Un mot est une suite de lettres, d'apostrophes (droite ou courbe) et de traits d'union.
// Le point, le point d'exclamation et le point d'interrogation sont des mots à part.
// Tout le reste sépare les mots. Le drapeau `u` lit le texte par point de code.
const MOTIF = new RegExp(`[${LETTRES}'’-]+|[.!?]`, 'gu');

/** Découpe un texte en mots, en minuscules : « Le fer ! » donne ["le", "fer", "!"]. */
export function decouperMots(texte: string): string[] {
  return texte.toLowerCase().match(MOTIF) ?? [];
}

/**
 * Pour chaque mot, compte les mots qui le suivent.
 *
 * Les clés sont dans l'ordre où les mots apparaissent pour la première fois,
 * comme celles du dictionnaire Python ; les suivants d'un mot aussi, comme
 * dans un Counter.
 */
export function compterSuivants(mots: readonly string[]): Map<string, Map<string, number>> {
  const suivants = new Map<string, Map<string, number>>();
  // Chaque mot avec son voisin de droite, comme zip(mots, mots[1:]).
  for (let i = 0; i + 1 < mots.length; i++) {
    const mot = mots[i];
    const suivant = mots[i + 1];
    let compte = suivants.get(mot);
    if (compte === undefined) {
      compte = new Map<string, number>();
      suivants.set(mot, compte);
    }
    compte.set(suivant, (compte.get(suivant) ?? 0) + 1);
  }
  return suivants;
}

/** Les suivants d'un mot et leurs comptes, par compte décroissant, puis par point de code. */
export function suivantsTries(compte: ReadonlyMap<string, number>): [string, number][] {
  return [...compte].sort(([a, na], [b, nb]) => nb - na || comparerPointsDeCode(a, b));
}

/**
 * Le mot qui suit le plus souvent `mot`, ou null si rien ne le suit.
 *
 * En cas d'égalité, le plus petit dans l'ordre des points de code, comme
 * min(compte, key=lambda m: (-compte[m], m)) en Python.
 */
export function predire(suivants: ReadonlyMap<string, ReadonlyMap<string, number>>, mot: string): string | null {
  const compte = suivants.get(mot);
  if (compte === undefined || compte.size === 0) return null;
  let meilleur: string | null = null;
  let meilleurCompte = 0;
  for (const [m, n] of compte) {
    if (meilleur === null || n > meilleurCompte || (n === meilleurCompte && comparerPointsDeCode(m, meilleur) < 0)) {
      meilleur = m;
      meilleurCompte = n;
    }
  }
  return meilleur;
}

/**
 * La suite qui commence par `depart`, de `longueur` mots au plus ([] si
 * `longueur` <= 0).
 *
 * Elle s'arrête plus tôt quand rien ne suit le dernier mot. Si `depart` n'est
 * pas dans le texte, rien ne le suit : la suite vaut [depart].
 */
export function generer(
  suivants: ReadonlyMap<string, ReadonlyMap<string, number>>,
  depart: string,
  longueur: number,
): string[] {
  if (longueur <= 0) return [];
  const suite = [depart];
  while (suite.length < longueur) {
    const suivant = predire(suivants, suite[suite.length - 1]);
    if (suivant === null) break;
    suite.push(suivant);
  }
  return suite;
}

/**
 * L'indice du premier mot déjà vu plus tôt dans la suite, ou null.
 *
 * À partir de ce mot, la suite tourne en rond : le même mot est toujours
 * suivi du même mot.
 */
export function premiereReprise(suite: readonly string[]): number | null {
  const vus = new Set<string>();
  for (let i = 0; i < suite.length; i++) {
    if (vus.has(suite[i])) return i;
    vus.add(suite[i]);
  }
  return null;
}
