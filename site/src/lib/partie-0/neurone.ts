// Le neurone à seuil du chapitre 0.5, en TypeScript, pour l'atelier du neurone.
//
// C'est le jumeau exact de projets/0.5-reseau/premier_reseau/neurone.py :
// mêmes fonctions, mêmes opérations, dans le même ordre. Le fichier
// projets/0.5-reseau/tests/attendus.json, calculé par le Python, le prouve dans
// neurone.test.ts : le meilleur réglage de chaque porte, et le compte de
// chacun des 729 réglages de la grille. Si l'un des deux change, l'autre doit
// suivre.
//
// Pourquoi le résultat est le même au bit près : les entrées valent 0 ou 1, et
// le calcul n'utilise que × et +, que la norme IEEE 754 arrondit au plus juste
// dans les deux langages, dans le même ordre : w1 × x1, plus w2 × x2, plus b.
// Sur la grille (des multiples de 0,5), chaque résultat tombe même juste.
//
// L'entraînement du réseau 2-2-1 n'est pas refait ici : il passe par exp et
// log, dont le dernier chiffre change d'un système à l'autre. Le site lit ses
// pertes et ses prédictions dans les attendus.
//
// Ce module n'importe rien : un parcours de test peut l'importer (aucun ?raw,
// aucun .json, aucun astro:*).

/** Un point (x1, x2) : deux entrées qui valent 0 ou 1. */
export type Point = readonly [number, number];

/** Les portes logiques du chapitre, sous leur nom Python. */
export type Porte = 'et' | 'ou' | 'ou_exclusif';

/** Le meilleur compte, les poids (w1, w2) et le biais b : le tuple de meilleur_reglage. */
export type Reglage = [number, [number, number], number];

/** Les 4 points, dans l'ordre des réponses de PORTES. */
export const POINTS: readonly Point[] = [
  [0, 0],
  [0, 1],
  [1, 0],
  [1, 1],
];

/** La réponse attendue de chaque porte, point par point. */
export const PORTES: Readonly<Record<Porte, readonly number[]>> = {
  et: [0, 0, 0, 1], // 1 seulement si les deux entrées valent 1
  ou: [0, 1, 1, 1], // 1 si au moins une entrée vaut 1
  ou_exclusif: [0, 1, 1, 0], // 1 si une seule des deux entrées vaut 1
};

/** Les valeurs essayées pour w1, w2 et b : de −2 à 2, par pas de 0,5. */
export const GRILLE: readonly number[] = [-2.0, -1.5, -1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0];

/** La réponse du neurone : 1 si la somme pondérée est positive, 0 sinon. */
export function sortieSeuil(poids: readonly [number, number], biais: number, x: Point): number {
  return poids[0] * x[0] + poids[1] * x[1] + biais > 0 ? 1 : 0;
}

/** Le nombre de points, sur 4, où le neurone donne la réponse de la porte. */
export function bienClasses(poids: readonly [number, number], biais: number, porte: Porte): number {
  const attendus = PORTES[porte];
  let compte = 0;
  for (let i = 0; i < POINTS.length; i++) {
    if (sortieSeuil(poids, biais, POINTS[i]) === attendus[i]) {
      compte += 1;
    }
  }
  return compte;
}

/** Le meilleur compte de la grille, et le premier réglage (w1, w2), b qui l'atteint. */
export function meilleurReglage(porte: Porte): Reglage {
  let meilleur: Reglage = [-1, [0.0, 0.0], 0.0];
  for (const w1 of GRILLE) {
    for (const w2 of GRILLE) {
      for (const b of GRILLE) {
        const compte = bienClasses([w1, w2], b, porte);
        if (compte > meilleur[0]) {
          meilleur = [compte, [w1, w2], b]; // strictement : on garde le premier réglage trouvé
        }
      }
    }
  }
  return meilleur;
}
