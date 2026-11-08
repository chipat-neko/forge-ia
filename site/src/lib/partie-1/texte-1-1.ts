// Le texte du site et ce que le projet 1.1 en a tiré, pour le chapitre 1.1.
//
// Il vit à part de ngrammes.ts : les imports ?raw et .json passent par Vite, et
// un parcours Playwright, chargé par Node sans Vite, ne pourrait pas importer un
// module qui les contient. ngrammes.ts prend le texte en argument et reste pur ;
// les parcours lisent les fichiers par readFileSync.

import attendus from '../../../../projets/1.1-modele-de-langage/tests/attendus.json';
import texte from '../../../../projets/1.1-modele-de-langage/donnees/texte-du-site.txt?raw';
import { alphabet } from './ngrammes';

/** Le texte d'apprentissage : une copie exacte de projets/1.1-modele-de-langage/donnees/texte-du-site.txt. */
export const TEXTE_DU_SITE: string = texte;

/** L'alphabet du texte entier (apprentissage et validation), comme en Python. */
export const ALPHABET: readonly string[] = Object.freeze(alphabet(TEXTE_DU_SITE));

/** La perplexité de chaque ordre n, sur le texte d'apprentissage et sur celui de validation, calculée par le Python. */
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
