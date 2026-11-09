// Les perplexités du projet 1.1, calculées par le Python, pour le chapitre 1.1
// (le tableau et ses phrases, rendus à la construction).
//
// À part de texte-1-1.ts : ce module importe le fichier d'attendus (.json), que
// l'atelier du chapitre n'a pas à charger dans le navigateur. Un parcours
// Playwright ne l'importe pas : il lit les attendus par readFileSync.

import attendus from '../../../../projets/1.1-modele-de-langage/tests/attendus.json';

/** La perplexité de chaque ordre n, sur le texte d'entraînement et sur celui de validation, calculée par le Python. */
export interface PerplexiteDOrdre {
  n: number;
  entrainement: number;
  validation: number;
}

/**
 * Les perplexités du Python (section « ordres » des attendus), de n = 0 à
 * n = 6. Le site ne les recalcule pas : elles passent par exp et log, dont le
 * dernier chiffre change d'un système à l'autre.
 */
export const PERPLEXITES: readonly PerplexiteDOrdre[] = Object.freeze(
  attendus.ordres.map((o) =>
    Object.freeze({ n: o.n, entrainement: o.perplexite_entrainement, validation: o.perplexite_validation }),
  ),
);
