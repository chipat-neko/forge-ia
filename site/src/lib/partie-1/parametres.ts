// Le jumeau du comptage des paramètres du chapitre 1.4 (projets/1.4-transformer,
// transformer_pas_a_pas/compter.py) : la répartition des paramètres d'une taille de forge
// entre le plongement, l'attention, le MLP et les RMSNorm.
//
// Elle s'applique aux formes du calculateur (`Forme`, celles de PRESETS_FORGE dans
// calculateur/ton-ia.ts) et fait la même conversion que `preset()` de ce module : le
// vocabulaire est `vocabulaire`, la longueur de contexte est `contexte`. Le résultat est
// vérifié contre les attendus du Python (tests/attendus.json) pour chaque preset : ce sont
// des entiers, ils se comparent exactement.

import type { Forme } from '../calculateur/formules';
import { largeurCachee, nombreParametres } from '../calculateur/ton-ia';

/** Les paramètres de chaque famille, dans l'ordre de `repartition` du Python. */
export interface RepartitionParametres {
  /** Le plongement d'entrée, qui sert aussi de matrice de sortie : compté une fois. */
  plongement: number;
  /** q, k, v et la projection de sortie de chaque couche. */
  attention: number;
  /** Les trois matrices du MLP SwiGLU de chaque couche. */
  mlp: number;
  /** Deux RMSNorm par couche, plus la finale. */
  normes: number;
}

/**
 * Les paramètres d'une forme de forge, famille par famille. La somme vaut
 * `nombreParametres` du calculateur (donc `nombre_parametres` de forge). Refuse une forme que
 * forge refuserait (têtes qui ne divisent pas `dim`, tête de dimension impaire…).
 */
export function repartitionParametres(f: Forme): RepartitionParametres {
  // La conversion de preset() : même vérification des dimensions que le calculateur.
  nombreParametres({ tailleVocabulaire: f.vocabulaire, dim: f.dim, couches: f.couches, tetes: f.tetes, longueurContexte: f.contexte });
  return {
    plongement: f.vocabulaire * f.dim,
    attention: f.couches * 4 * f.dim * f.dim,
    mlp: f.couches * 3 * f.dim * largeurCachee(f.dim),
    normes: f.couches * 2 * f.dim + f.dim,
  };
}

/**
 * Les nombres de têtes que le chapitre propose pour une largeur `dim` : ceux qui partagent
 * `dim` en têtes égales (`dim % t === 0`) dont la dimension est paire (`(dim / t) % 2 === 0`),
 * puisque RoPE tourne les valeurs par paires. Dans l'ordre croissant.
 */
export function nombresDeTetes(dim: number): number[] {
  if (!(Number.isSafeInteger(dim) && dim >= 1)) {
    throw new RangeError(`nombresDeTetes${'\u202F'}: \`dim\` vaut ${String(dim)}${'\u202F'}: il doit être un entier d’au moins 1.`);
  }
  const resultat: number[] = [];
  for (let t = 1; t <= dim; t++) {
    if (dim % t === 0 && (dim / t) % 2 === 0) resultat.push(t);
  }
  return resultat;
}
