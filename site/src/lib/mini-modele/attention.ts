// L'attention : les scores, le softmax et le mélange des valeurs.
//
// C'est le jumeau exact de projets/mini-modele/mini_modele/attention.py :
// mêmes fonctions, mêmes boucles, même ordre des opérations. Les attendus du
// modèle (tests/attendus-modele.json), qui passent par ces fonctions à chaque
// tête et à chaque position, le prouvent au bit près dans modele.test.ts.
//
// Ces fonctions servent deux fois : dans le mini-modèle (modele.ts), et dans
// l'animation de l'attention, qui montre leurs résultats pas à pas.
//
// Une seule convention : une requête pose la question, et le score d'une clé
// vaut requête · clé, multiplié par l'échelle (1 / √ de la taille d'une tête).
// Le masque causal ne se calcule pas : l'appelant ne passe que les clés
// visibles, celles des positions jusqu'à la requête comprise.
// Ce fichier est vérifié par sources.test.ts.

import { exp, maximum, produitScalaire, somme } from './calcul';

/** Le score de chaque clé visible, dans l'ordre des clés : requête · clé, fois l'échelle (région `scores`). */
export function scoresAttention(
  requete: ArrayLike<number>,
  cles: readonly ArrayLike<number>[],
  echelle: number,
): number[] {
  return cles.map((cle) => produitScalaire(requete, cle) * echelle);
}

/**
 * Des scores aux poids : chaque poids est positif, et leur somme vaut 1 (région `softmax`).
 *
 * On retire d'abord le plus grand score m : les poids ne changent pas, et
 * exp(s − m) ne dépasse jamais 1, donc rien ne déborde.
 */
export function softmax(scores: ArrayLike<number>): number[] {
  const m = maximum(scores);
  const e = Array.from(scores, (s) => exp(s - m));
  const total = somme(e);
  return e.map((v) => v / total);
}

/** Les poids d'attention de la requête sur les clés visibles : le softmax de leurs scores. */
export function poidsAttention(
  requete: ArrayLike<number>,
  cles: readonly ArrayLike<number>[],
  echelle: number,
): number[] {
  return softmax(scoresAttention(requete, cles, echelle));
}

/** Autant de poids que de valeurs, au moins une valeur, et des valeurs de même longueur. */
export function verifierValeurs(poids: ArrayLike<number>, valeurs: readonly ArrayLike<number>[]): void {
  if (poids.length !== valeurs.length) {
    throw new RangeError(
      `melanger_valeurs : il faut autant de poids que de valeurs (reçu ${poids.length} et ${valeurs.length}).`,
    );
  }
  if (valeurs.length === 0) {
    throw new RangeError(
      'melanger_valeurs : il faut au moins une valeur (la position de la requête est toujours visible).',
    );
  }
  for (const valeur of valeurs) {
    if (valeur.length !== valeurs[0].length) {
      throw new RangeError(
        "melanger_valeurs : les valeurs n'ont pas toutes la même longueur " +
          `(${valeurs[0].length} et ${valeur.length}). Donne des valeurs de même longueur.`,
      );
    }
  }
}

/**
 * La sortie de la tête : les valeurs, mélangées selon les poids (région `melange`).
 *
 * Pour chaque composante d : poids[0] × valeurs[0][d] + poids[1] × valeurs[1][d] + …
 */
export function melangerValeurs(poids: ArrayLike<number>, valeurs: readonly ArrayLike<number>[]): number[] {
  verifierValeurs(poids, valeurs);
  const sortie: number[] = [];
  for (let d = 0; d < valeurs[0].length; d++) {
    let s = 0.0;
    for (let j = 0; j < poids.length; j++) {
      s += poids[j] * valeurs[j][d];
    }
    sortie.push(s);
  }
  return sortie;
}
