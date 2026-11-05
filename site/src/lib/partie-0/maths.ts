// Les maths utiles du chapitre 0.2, en TypeScript, pour les figures du navigateur.
//
// C'est le jumeau exact de projets/0.2-maths/maths_utiles/ (vecteurs.py,
// derivees.py et tirage.py) : mêmes fonctions, mêmes opérations, dans le même
// ordre. Le fichier projets/0.2-maths/tests/attendus.json, calculé par le
// Python, le prouve dans maths.test.ts, et la page d'essai de parité le vérifie
// dans Chrome, Firefox et WebKit. Si l'un des deux change, l'autre doit suivre.
//
// Pourquoi le résultat est le même au bit près : les entrées sont des entiers
// ou des demi-entiers, et les calculs n'utilisent que + − × ÷ et la racine
// carrée, que la norme IEEE 754 arrondit au plus juste dans les deux langages.
// Les sommes se font dans une boucle, de gauche à droite, comme en Python. Ni
// exp ni log : softmax, −ln p, la pente approchée et la règle de la chaîne
// restent en Python, et le site lit leurs valeurs dans les attendus.
//
// Le hasard est le Hasard (SplitMix32) du mini-modèle : le Python de 0.2 en
// garde une copie, et la même graine donne la même suite des deux côtés.
//
// Ce module n'importe que calcul.ts, qui n'importe rien : un parcours de test
// peut l'importer (aucun ?raw, aucun .json).

import { Hasard } from '../mini-modele/calcul';

const FINE = '\u202F';

/** « 1 colonne », « 4 colonnes » : le mot prend un s à partir de 2. */
function quantite(n: number, mot: string): string {
  return n <= 1 ? `${n} ${mot}` : `${n} ${mot}s`;
}

/** Arrête le calcul si les deux vecteurs n'ont pas la même taille (zip(…, strict=True) en Python). */
function verifierTailles(a: readonly number[], b: readonly number[]): void {
  if (a.length !== b.length) {
    throw new RangeError(
      `Les deux vecteurs n’ont pas la même taille (${a.length} et ${b.length} nombres)${FINE}: il en faut autant.`,
    );
  }
}

/** La somme des produits, case par case : (3, 1) · (1, 2) = 3 × 1 + 1 × 2 = 5. */
export function produitScalaire(a: readonly number[], b: readonly number[]): number {
  verifierTailles(a, b);
  let s = 0.0;
  for (let i = 0; i < a.length; i++) {
    s += a[i] * b[i];
  }
  return s;
}

/** La longueur du vecteur : la racine carrée de a · a. */
export function norme(a: readonly number[]): number {
  return Math.sqrt(produitScalaire(a, a));
}

/**
 * Le cosinus de l'angle entre a et b, de −1 à 1 : produit scalaire ÷ (norme de
 * a × norme de b). null si l'un des deux est nul : un vecteur nul n'a pas de
 * direction.
 */
export function cosinus(a: readonly number[], b: readonly number[]): number | null {
  const na = norme(a);
  const nb = norme(b);
  if (na === 0.0 || nb === 0.0) return null;
  return produitScalaire(a, b) / (na * nb);
}

/** La somme case par case : (3, 1) + (1, 2) = (4, 3). */
export function somme(a: readonly number[], b: readonly number[]): number[] {
  verifierTailles(a, b);
  return a.map((x, i) => x + b[i]);
}

/**
 * Chaque ligne de la matrice fois le vecteur : un produit scalaire par case du
 * résultat. [[1, 2, 3], [0, 1, 0]] × [1, 1, 1] = [6, 1]. Une ligne qui n'a pas
 * autant de nombres que le vecteur arrête le calcul, avec le message du Python.
 */
export function matriceFoisVecteur(m: readonly (readonly number[])[], v: readonly number[]): number[] {
  const resultat: number[] = [];
  for (const ligne of m) {
    if (ligne.length !== v.length) {
      throw new RangeError(
        `La matrice a ${quantite(ligne.length, 'colonne')} et le vecteur ${quantite(v.length, 'nombre')}` +
          `${FINE}: il en faut autant.`,
      );
    }
    resultat.push(produitScalaire(ligne, v));
  }
  return resultat;
}

/** Les taux de la figure de la descente, du plus prudent au plus grand. */
export const TAUX_DESCENTE: readonly number[] = Object.freeze([0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 1.0, 1.05, 1.2]);

/** L'erreur selon le poids x : (x − 3)² + 1, la plus petite (1) en x = 3. */
export function erreur(x: number): number {
  return (x - 3.0) * (x - 3.0) + 1.0;
}

/** La pente exacte de l'erreur en x : 2 × (x − 3). Négative à gauche de 3, positive à droite. */
export function pente(x: number): number {
  return 2.0 * (x - 3.0);
}

/** Les positions de la descente : x0, puis une par pas, avec x ← x − taux × pente(x). */
export function descendre(x0: number, taux: number, nbPas: number): number[] {
  const positions = [x0];
  let x = x0;
  for (let n = 0; n < nbPas; n++) {
    x = x - taux * pente(x);
    positions.push(x);
  }
  return positions;
}

/**
 * Le premier pas n où l'erreur passe sous le seuil (0 si x0 y est déjà), ou
 * null si la descente n'y arrive pas en maxPas pas : elle oscille, ou elle
 * s'éloigne du fond.
 */
export function pasPourAtteindre(x0: number, taux: number, seuil: number, maxPas = 100): number | null {
  let x = x0;
  for (let n = 0; n <= maxPas; n++) {
    if (erreur(x) < seuil) return n;
    x = x - taux * pente(x);
  }
  return null;
}

/** Ce qui suit « le » dans un petit texte, avec le nombre de fois (l'ordre du dictionnaire Python). */
export const EXEMPLE_COMPTES: readonly (readonly [string, number])[] = Object.freeze([
  Object.freeze(['fer', 6] as const),
  Object.freeze(['métal', 3] as const),
  Object.freeze(['feu', 1] as const),
]);

/** La graine de départ de la figure des tirages et du pari. */
export const GRAINE_TIRAGE = 1234;

/** Chaque compte divisé par le total : fer 6, métal 3, feu 1 donnent [0.6, 0.3, 0.1]. */
export function probabilites(comptes: readonly (readonly [string, number])[]): number[] {
  // Des entiers : la somme est exacte, dans n'importe quel ordre.
  let total = 0;
  for (const [, c] of comptes) total += c;
  return comptes.map(([, c]) => c / total);
}

/**
 * L'issue tirée par u, un nombre de [0, 1[ : les probabilités sont posées bout
 * à bout de 0 à 1, et u tombe dans l'une d'elles. Si les arrondis laissent le
 * cumul un peu sous 1, un u au-delà prend la dernière issue.
 */
export function tirer(probas: readonly number[], u: number): number {
  let cumul = 0.0;
  for (let i = 0; i < probas.length; i++) {
    cumul += probas[i];
    if (u < cumul) return i;
  }
  return probas.length - 1;
}

/** n tirages au sort, avec un Hasard neuf de cette graine : combien de fois chaque issue est sortie. */
export function tirages(probas: readonly number[], n: number, graine: number): number[] {
  const hasard = new Hasard(graine);
  const comptes: number[] = probas.map(() => 0);
  for (let k = 0; k < n; k++) {
    comptes[tirer(probas, hasard.uniforme())] += 1;
  }
  return comptes;
}
