// La marge et le verdict des QCM du chapitre 1.6 : le jumeau TypeScript de la région « marge » de
// projets/1.6-evaluation/evaluation_pas_a_pas/pas_a_pas.py, avec les mêmes opérations dans le même
// ordre. marge95 est la marge de Wald (une racine carrée, exacte dans les deux langages) ;
// verdictQcm est la règle du rapport de forge : l'exactitude NORMALISÉE comparée au hasard, avec la
// marge du HASARD. evaluation.test.ts les compare, sans tolérance, à la grille de
// projets/1.6-evaluation/tests/attendus.json.
//
// Ce module n'importe rien : l'atelier des QCM (un îlot Svelte, dans le navigateur) peut s'en
// servir, par paris-1-6.ts, sans embarquer node:fs. evaluation.ts, qui lit les relevés sur le
// disque, le réexporte.

/** Où est l'exactitude par rapport au hasard : au-dessus, à moins d'une marge (pas-different), ou en dessous. */
export type Verdict = 'au-dessus' | 'pas-different' | 'en-dessous';

/** 1,96 : l'intervalle à 95 % d'une loi normale va de −1,96 à +1,96 écarts-types. */
export const Z_95 = 1.96;

/**
 * La demi-largeur de l'intervalle à 95 % d'une exactitude mesurée sur `n` questions (marge de Wald) :
 * 1,96 × √(p (1 − p) / n). Elle s'annule quand l'exactitude vaut 0 ou 1.
 */
export function marge95(exactitude: number, n: number): number {
  return Z_95 * Math.sqrt((exactitude * (1 - exactitude)) / n);
}

/** La demi-largeur de l'intervalle à 95 % d'un tirage au sort sur `n` questions de `choix` choix chacune. */
export function margeHasard(n: number, choix = 4): number {
  const p = 1 / choix;
  return (Z_95 * Math.sqrt(n * (p * (1 - p)))) / n;
}

/**
 * Le verdict de forge (forge.evaluation.rapport.verdict) : l'exactitude (normalisée) moins le hasard,
 * comparée à la marge du HASARD (margeHasard, ou `marge_hasard` du rapport), pas à celle de la mesure.
 */
export function verdictQcm(exactitude: number, hasard: number, marge: number): Verdict {
  const ecart = exactitude - hasard;
  if (ecart > marge) return 'au-dessus';
  if (ecart < -marge) return 'en-dessous';
  return 'pas-different';
}
